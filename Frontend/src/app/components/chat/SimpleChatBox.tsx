'use client';

import { useMemo, useRef, useCallback, useEffect, useState, memo, MouseEvent, TouchEvent } from 'react';
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';
import { ChatBoxProps } from '@/app/types/chat';
import styles from './SimpleChatBox.module.css';
import { ChatInput, PendingActions, MessageBubble } from '.';
import { CHAT_THEME } from './chatTheme';
import useVoiceInterface from './hooks/useVoiceInterface';
import { useEventSimulation } from './hooks/useEventSimulation';
import { chatLogger } from '@/app/utils/ChatBoxLogger';
import { ANIMATION_CONFIG } from '../../config/morphingConfig';
import {
  filterRegularMessages,
  getMorphingClasses,
  getEventClasses,
  getFriendlyAgentName,
  buildAgentTaskEvents,
  type ReasoningPlanStep,
  type SimulatedEvent
} from '@/app/utils/chatHelpers';

// Tipos para mayor seguridad
interface MessageWithPayload {
  payload?: Record<string, unknown>;
  [key: string]: unknown;
}

// Funciones de ayuda para extraer informacion del plan razonado
const extractReasoningPlanSteps = (message: MessageWithPayload): ReasoningPlanStep[] => {
  if (!message || typeof message !== 'object') {
    return [];
  }

  const payload = message.payload ?? message;
  const planContainers: Array<Record<string, unknown>> = [
    payload?.response_metadata,
    payload?.meta,
    payload?.reasoning_plan,
    payload?.data?.reasoning_plan,
    payload?.data,
    payload?.metadata
  ];

  for (const container of planContainers) {
    if (!container || typeof container !== 'object') {
      continue;
    }

    const plan =
      container.reasoning_plan && typeof container.reasoning_plan === 'object'
        ? container.reasoning_plan
        : container;

    const steps = (plan as Record<string, unknown>)?.steps;
    if (Array.isArray(steps) && steps.length > 0) {
      return steps as ReasoningPlanStep[];
    }
  }

  return [];
};

// Función eliminada - usando getActionType mejorado de chatHelpers

function SimpleChatBox({ sucursal, onRemoveSucursal }: ChatBoxProps) {
  const {
    messages,
    loading,
    sendCommand,
    pendingActions,
    approvalReason,
    submitAction,
    appendLocalMessage,
    activeSessionId,
    agentEvents,  // Eventos directos del WebSocket de agentes
  } = useGlobalChat();

  const feedRef = useRef<HTMLDivElement>(null);
  const completedEventIdsRef = useRef<Set<string>>(new Set());
  const [archivedEvents, setArchivedEvents] = useState<SimulatedEvent[]>([]);

  // Ref para mantener estado actualizado y evitar stale closures
  const messagesRef = useRef(messages);
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  // Hook personalizado para manejar toda la simulación de eventos
  const {
    simState,
    simulateEventStreaming,
    simulatePlanSteps,
    simulateCustomEvents,
    startMorphingSequence,
    handleBatchComplete,
    resetForNewMessage,
    stopWaiting
  } = useEventSimulation();

  // Voice interface
  const {
    beginVoiceRecording,
    finishVoiceRecording,
    isRecording,
    isProcessing,
    isMicPressed,
    voiceNotice,
    partialTranscript,
    autoPlayError,
  } = useVoiceInterface({
    sessionId: activeSessionId ?? 'global',
    onMessageAppend: (entry: { content?: string } | null) => {
      const content = typeof entry?.content === 'string' ? entry.content.trim() : '';
      if (content) {
        appendLocalMessage({
          id: `voice-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          role: entry?.role === 'user' ? 'user' : 'agent',
          content,
          agent: entry?.metadata?.agent,
        });
      }
    },
  });

  // Funciones movidas a useEventSimulation hook para evitar duplicación

  const handleSendMessage = useCallback(async (text: string) => {
    if (!text.trim()) return;

    chatLogger.info('Enviando mensaje', { text });

    try {
      // Limpiar estado anterior y preparar para nueva simulación
      completedEventIdsRef.current.clear();
      resetForNewMessage(text);

      // Iniciar morphing text inmediatamente
      startMorphingSequence();

      // Enviar al backend (sendCommand ya agrega el mensaje del usuario)
      await sendCommand(text);
    } catch (error) {
      chatLogger.error('Error al enviar mensaje', { error, text });
      // El error ya se maneja en sendCommand, pero lo registramos
      // No detenemos el morphing para mantener la UI responsiva
    }
  }, [sendCommand, startMorphingSequence, resetForNewMessage]);

  // Filtrar mensajes regulares (no eventos) - usando helper
  const regularMessages = useMemo(() => {
    return filterRegularMessages(messages);
  }, [messages]);

  // Detectar cuando llegan eventos batch y el mensaje final
  useEffect(() => {
    console.log('🔍 CONDICIONES SIMULACIÓN:', {
      loading,
      isWaitingForBatch: simState.isWaitingForBatch,
      morphingPhase: simState.morphingPhase,
      CUMPLE_ORIGINAL: !loading && simState.isWaitingForBatch && simState.morphingPhase === 'waiting',
      CUMPLE_RELAJADO: !loading && simState.isWaitingForBatch
    });

    // CAMBIO CRÍTICO: Relajamos la condición para activar simulación
    // No requerimos morphingPhase === 'waiting' porque puede haber terminado
    if (!loading && simState.isWaitingForBatch) {
      console.log('✅ ACTIVANDO SIMULACIÓN DE EVENTOS');
      chatLogger.debug('Loading terminó, buscando eventos');

      /**
       * CAMBIO CRÍTICO: Usamos eventos directos del WebSocket (agentEvents)
       * en lugar de filtrar desde messages. Esto evita duplicación y asegura
       * que trabajamos con datos reales del backend.
       * @see GlobalChatContext para la fuente de agentEvents
       */
      const recentAgentEvents = agentEvents.slice(-30); // Últimos 30 eventos reales del WebSocket

      // Buscar el mensaje final de respuesta
      const finalMessage = messages.slice(-10).find(msg => {
        // Es un mensaje con contenido o texto
        const hasContent = msg.content || msg.text;
        // No es del usuario
        const notUser = msg.role !== 'user' && msg.sender !== 'user';
        // No es un evento de agente
        const notEvent = !msg.payload?.type || !msg.payload?.type.includes('event');
        // Es una respuesta final (puede venir del orquestador también)
        const isResponse = msg.role === 'agent' || msg.sender === 'bot';

        return hasContent && notUser && notEvent && isResponse;
      });

      let planSteps: ReasoningPlanStep[] = [];
      for (let index = messages.length - 1; index >= 0; index -= 1) {
        const candidateSteps = extractReasoningPlanSteps(messages[index]);
        if (candidateSteps.length > 0) {
          planSteps = candidateSteps;
          break;
        }
      }

      chatLogger.debug('Eventos encontrados', {
        count: recentAgentEvents.length,
        hasFinalMessage: !!finalMessage,
        planSteps: planSteps.length
      });

      let finalizeTimer: ReturnType<typeof setTimeout> | undefined;
      let finalMessageTimer: ReturnType<typeof setTimeout> | undefined;

      const queueFinalMessage = () => {
        if (finalMessage && (finalMessage.content || finalMessage.text)) {
          // Check if already shown at the time of execution, not before
          const isAlreadyShown = regularMessages.some(msg => {
            if (finalMessage.id && msg.id) {
              return msg.id === finalMessage.id;
            }
            const msgText = msg.content || msg.text;
            return (
              msgText &&
              (finalMessage.content || finalMessage.text) &&
              msgText === (finalMessage.content || finalMessage.text)
            );
          });

          if (!isAlreadyShown) {
            finalMessageTimer = window.setTimeout(() => {
              /**
               * CAMBIO CRÍTICO: Doble verificación para evitar race conditions.
               * Verificamos nuevamente dentro del timeout por si el mensaje
               * se agregó mientras esperábamos.
               */
              // Segunda verificación usando ref para estado actualizado
              const currentMessages = messagesRef.current;
              const stillNotShown = !currentMessages.some(msg => {
                if (finalMessage.id && msg.id) {
                  return msg.id === finalMessage.id;
                }
                const msgText = msg.content || msg.text;
                return (
                  msgText &&
                  (finalMessage.content || finalMessage.text) &&
                  msgText === (finalMessage.content || finalMessage.text)
                );
              });

              if (stillNotShown) {
                appendLocalMessage({
                  id: finalMessage.id || `final-${Date.now()}`,
                  role: 'agent' as const,
                  content: finalMessage.content || finalMessage.text || '',
                  agent: finalMessage.agent || 'assistant'
                });
              }
            }, ANIMATION_CONFIG.timings.finalDisplay);
          }
        }
      };

      const taskEvents = buildAgentTaskEvents({ agentEvents: recentAgentEvents, planSteps, finalMessage });

      // DIAGNÓSTICO: Ver qué datos tenemos
      console.log('🔍 DIAGNÓSTICO SIMULACIÓN:', {
        recentAgentEvents: recentAgentEvents.length,
        taskEvents: taskEvents.length,
        planSteps: planSteps.length,
        finalMessage: !!finalMessage,
        simState: simState,
        agentEventsDetail: recentAgentEvents.slice(0, 3) // Primeros 3 para ver estructura
      });

      let simulationDuration = 0;

      if (taskEvents.length > 0) {
        chatLogger.debug('Simulando tareas con datos reales', { count: taskEvents.length });
        console.log('✅ Ejecutando simulateCustomEvents con:', taskEvents);
        simulationDuration = simulateCustomEvents(taskEvents);
      } else if (recentAgentEvents.length > 0) {
        chatLogger.debug('Simulando eventos de agentes', { count: recentAgentEvents.length });
        console.log('✅ Ejecutando simulateEventStreaming con:', recentAgentEvents);
        simulationDuration = simulateEventStreaming(recentAgentEvents, simState.originalQuery);
      } else if (planSteps.length > 0) {
        chatLogger.debug('Simulando tareas desde reasoning plan', { steps: planSteps.length });
        console.log('✅ Ejecutando simulatePlanSteps con:', planSteps);
        simulationDuration = simulatePlanSteps(planSteps);
      } else {
        chatLogger.debug('No hay tareas ni eventos para simular');
        console.log('⚠️ NO HAY EVENTOS PARA SIMULAR');
      }

      stopWaiting();

      if (simulationDuration > 0) {
        const finalDelay =
          simulationDuration +
          ANIMATION_CONFIG.timings.shimmerDuration +
          ANIMATION_CONFIG.timings.finalDisplay;

        finalizeTimer = window.setTimeout(() => {
          // Usar el último texto del morphing para persistirlo
          handleBatchComplete(appendLocalMessage);
          queueFinalMessage();
        }, finalDelay);
      } else {
        handleBatchComplete(appendLocalMessage);
        queueFinalMessage();
      }

      return () => {
        if (finalizeTimer) {
          clearTimeout(finalizeTimer);
        }
        if (finalMessageTimer) {
          clearTimeout(finalMessageTimer);
        }
      };
    }
  }, [
    // Dependencias esenciales para el trigger
    loading,
    simState.isWaitingForBatch,
    simState.morphingPhase,
    // Datos necesarios para procesamiento
    messages,
    agentEvents,
    // Callbacks estables (no deberían cambiar)
    simulateEventStreaming,
    simulatePlanSteps,
    simulateCustomEvents,
    handleBatchComplete,
    stopWaiting,
    appendLocalMessage,
    // Derivados - considerar memoización adicional
    regularMessages,
    simState.originalQuery
  ]);

  // Persistir eventos completados para que queden visibles en el timeline
  useEffect(() => {
    simState.simulatedEvents.forEach(event => {
      if (event.status !== 'completed') {
        return;
      }
      if (completedEventIdsRef.current.has(event.id)) {
        return;
      }

      completedEventIdsRef.current.add(event.id);

      setArchivedEvents(prev => {
        const alreadyStored = prev.some(item => item.id === event.id);
        if (alreadyStored) {
          return prev;
        }
        return [...prev, { ...event, status: 'completed' }];
      });
    });
  }, [simState.simulatedEvents]);

  const handleSubmitAction = useCallback(async (params: { actionId: string; approved: boolean }) => {
    await submitAction(params);
  }, [submitAction]);

  const handlePressStart = useCallback((event: MouseEvent<HTMLButtonElement> | TouchEvent<HTMLButtonElement>) => {
    event.preventDefault();
    beginVoiceRecording();
  }, [beginVoiceRecording]);

  const handlePressEnd = useCallback((event: MouseEvent<HTMLButtonElement> | TouchEvent<HTMLButtonElement>) => {
    event.preventDefault();
    finishVoiceRecording();
  }, [finishVoiceRecording]);

  // Scroll automático
  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [messages, simState.simulatedEvents, simState.currentEventIndex, simState.morphingText]);

  // Renderizar mensajes regulares (no eventos)
  return (
    <div className={styles.container} role="region" aria-label="Chat">
      <div
        ref={feedRef}
        className={styles.feed}
        role="log"
        aria-live="polite"
        aria-label="Mensajes del chat"
      >
        {/* Info de sucursal si existe */}
        {sucursal && (
          <div className={styles.sucursalCard}>
            <span>
              Sucursal: {sucursal.name}
            </span>
            {onRemoveSucursal && (
              <button onClick={onRemoveSucursal}>
                Quitar
              </button>
            )}
          </div>
        )}

        {/* Mensajes regulares */}
        {regularMessages.map(msg => (
          <MessageBubble
            key={msg.id || Math.random()}
            message={{
              id: msg.id || '',
              sender: msg.role === 'user' ? 'user' : msg.role === 'system' ? 'bot' : 'bot',
              text: msg.content || msg.text || '',
              agent: msg.agent,
              timestamp: msg.timestamp || Date.now(),
            }}
          />
        ))}

        {/* Morphing text del orquestador */}
        {simState.morphingText && simState.morphingPhase && (
          <div className={styles.orchestratorMessage}>
            <span
              key={simState.morphingKey}
              className={getMorphingClasses(styles, simState.morphingPhase)}
            >
              {simState.morphingText}
            </span>
            <div className={styles.processingIndicator}>
              <span className={styles.processingDot} />
              <span className={styles.processingDot} />
              <span className={styles.processingDot} />
            </div>
          </div>
        )}

        {/* Eventos simulados con streaming visual y mensajes contextuales */}
        {console.log('🎨 RENDERIZANDO EVENTOS:', simState.simulatedEvents.length, simState.simulatedEvents)}
        {(() => {
          const timelineEvents = [...archivedEvents, ...simState.simulatedEvents];
          return timelineEvents.map((event, idx) => {
            if (event.status === 'pending') return null;

            const showHeader =
              idx === 0 ||
              (idx > 0 && timelineEvents[idx - 1].agent !== event.agent);

            const { containerClass, bulletClass, textClass } = getEventClasses(styles, event.status);

            return (
              <div key={event.id}>
              {showHeader && (
                <div className={styles.agentHeader}>
                  {event.friendlyName || getFriendlyAgentName(event.agent)}
                </div>
              )}
              <div className={containerClass}>
                <div className={bulletClass} />
                <div className={styles.eventBody}>
                  <span className={textClass}>
                    {event.primaryText}
                  </span>
                  {event.detail && (
                    <span className={styles.eventDetail}>
                      {event.detail}
                    </span>
                  )}
                </div>
              </div>
            </div>
            );
          });
        })()}
      </div>

      {/* Acciones pendientes */}
      {pendingActions.length > 0 && (
        <PendingActions
          pendingActions={pendingActions}
          approvalReason={approvalReason}
          onSubmitAction={handleSubmitAction}
          loading={loading}
        />
      )}

      {/* Voice status */}
      {(voiceNotice || partialTranscript || autoPlayError) && (
        <div className={styles.voiceStatus}>
          <span className={styles.voiceError}>
            {voiceNotice || partialTranscript || autoPlayError}
          </span>
        </div>
      )}

      {/* Chat input */}
      <ChatInput
        onSend={handleSendMessage}
        loading={loading}
        rightSlot={
          <button
            className={`${styles.micButton} ${isMicPressed ? styles.pressed : ''} ${isRecording ? styles.recording : ''}`}
            onMouseDown={handlePressStart}
            onMouseUp={handlePressEnd}
            onTouchStart={handlePressStart}
            onTouchEnd={handlePressEnd}
            title="Mantén presionado para grabar"
            disabled={loading || isProcessing}
            aria-label={isRecording ? "Grabando voz" : "Mantén presionado para grabar"}
            aria-pressed={isMicPressed}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="white"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
              <line x1="12" y1="19" x2="12" y2="23" />
              <line x1="8" y1="23" x2="16" y2="23" />
            </svg>
          </button>
        }
      />
    </div>
  );
}

// Exportar con memo para optimizar re-renders
// Solo re-renderiza si cambia sucursal o onRemoveSucursal
export default memo(SimpleChatBox, (prevProps, nextProps) => {
  return (
    prevProps.sucursal === nextProps.sucursal &&
    prevProps.onRemoveSucursal === nextProps.onRemoveSucursal
  );
});


