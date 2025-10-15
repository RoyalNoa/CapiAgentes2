'use client';

<<<<<<< HEAD
import { useMemo, useRef, useCallback, useEffect, useState, memo, MouseEvent, TouchEvent } from 'react';
=======
import {
  useMemo,
  useRef,
  useCallback,
  useEffect,
  useState,
  memo,
  MouseEvent,
  TouchEvent,
} from 'react';
>>>>>>> origin/develop
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';
import { ChatBoxProps } from '@/app/types/chat';
import styles from './SimpleChatBox.module.css';
import { ChatInput, PendingActions, MessageBubble } from '.';
<<<<<<< HEAD
import { CHAT_THEME } from './chatTheme';
=======
>>>>>>> origin/develop
import useVoiceInterface from './hooks/useVoiceInterface';
import { useEventSimulation } from './hooks/useEventSimulation';
import { chatLogger } from '@/app/utils/ChatBoxLogger';
import { ANIMATION_CONFIG } from '../../config/morphingConfig';
import {
<<<<<<< HEAD
  filterRegularMessages,
=======
>>>>>>> origin/develop
  getMorphingClasses,
  getEventClasses,
  getFriendlyAgentName,
  buildAgentTaskEvents,
<<<<<<< HEAD
  type ReasoningPlanStep
} from '@/app/utils/chatHelpers';

// Tipos para mayor seguridad
=======
  type ReasoningPlanStep,
  type SimulatedEvent,
} from '@/app/utils/chatHelpers';
import type { OrchestratorMessage } from '@/app/utils/orchestrator/useOrchestratorChat';
import type { AgentEvent } from '@/app/hooks/useAgentWebSocket';

type SimulationStatus = 'idle' | 'running' | 'complete';

interface TurnSimulation {
  events: SimulatedEvent[];
  status: SimulationStatus;
  collapsed: boolean;
  startEventIndex: number;
}

interface ChatTurn {
  id: string;
  userMessage: OrchestratorMessage;
  agentMessages: OrchestratorMessage[];
  decisions: OrchestratorMessage[];
  simulation: TurnSimulation;
}

>>>>>>> origin/develop
interface MessageWithPayload {
  payload?: Record<string, unknown>;
  [key: string]: unknown;
}

<<<<<<< HEAD
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

=======
interface TurnBlockProps {
  turn: ChatTurn;
  isActive: boolean;
  liveEvents: SimulatedEvent[];
  morphingText?: string | null;
  morphingPhase?: string | null;
  morphingKey?: number;
  onToggle: (turnId: string) => void;
}

const DECISION_SUFFIX_PATTERNS = [
  /^(?:no\s+guardar[ée]|no\s+guardare)/i,
  /^(?:procedo|proceder[ée]|procedemos)\b/i,
  /^(?:decisi[oó]n (?:registrada|confirmada))/i,
];

const HUMAN_GATE_QUESTION_PATTERNS = [
  /¿\s*quer(?:e|é)s.+guardar.+json\??$/i,
  /¿\s*quer(?:e|é)s.+guardar.+escritorio\??$/i,
  /¿\s*quer(?:e|é)s.+abrir.+escritorio\??$/i,
];

const stripAccents = (value: string) => value.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

const canonicalizeText = (value: string): string =>
  stripAccents(value).toLowerCase().replace(/\s+/g, ' ').trim();

const splitDecisionSuffix = (raw?: string) => {
  if (typeof raw !== 'string') {
    return { cleaned: '', decision: null as string | null };
  }

  const trimmed = raw.trim();
  if (!trimmed) {
    return { cleaned: '', decision: null as string | null };
  }

  const lines = trimmed.split(/\r?\n/).map(line => line.trim()).filter(Boolean);
  if (lines.length === 0) {
    return { cleaned: '', decision: null as string | null };
  }

  const lastLine = lines[lines.length - 1];
  const matchesDecision = DECISION_SUFFIX_PATTERNS.some(pattern => pattern.test(lastLine));
  if (!matchesDecision || lines.length === 1) {
    return { cleaned: trimmed, decision: null as string | null };
  }

  const cleanedLines = lines.slice(0, -1);
  const cleaned = cleanedLines.join('\n').trim();
  if (!cleaned) {
    return { cleaned: trimmed, decision: null as string | null };
  }

  return {
    cleaned,
    decision: lastLine,
  };
};

const stripTrailingQuestion = (value: string): string => {
  const lines = value.split(/\r?\n/).map(line => line.trim());
  while (lines.length > 0) {
    const lastLine = lines[lines.length - 1];
    if (HUMAN_GATE_QUESTION_PATTERNS.some(pattern => pattern.test(lastLine))) {
      lines.pop();
      continue;
    }
    break;
  }
  return lines.join('\n').trim();
};

const normalizeMessageText = (value: unknown): string => {
  if (typeof value !== 'string') {
    return '';
  }
  return value.trim().replace(/\s+/g, ' ').toLowerCase();
};

const getMessageKey = (message: any): string => {
  if (!message || typeof message !== 'object') {
    return 'unknown';
  }

  if (typeof message.id === 'string' && message.id.trim().length > 0) {
    return message.id.trim();
  }

  const role = typeof message.role === 'string' ? message.role : 'message';
  const contentCandidate = message.content ?? message.text ?? '';
  const normalizedContent = normalizeMessageText(contentCandidate);

  if (normalizedContent.length > 0) {
    return `${role}:${normalizedContent}`;
  }

  const timestamp = typeof message.timestamp === 'number' ? message.timestamp : Date.now();
  return `${role}:ts:${timestamp}`;
};

const gatherComparableStrings = (message: OrchestratorMessage): string[] => {
  const payload = (message as any)?.payload ?? {};
  const meta = payload?.metadata ?? payload?.meta ?? {};
  const responseMeta = payload?.response_metadata ?? {};

  const fragments: Array<string | undefined> = [
    message.content,
    payload?.respuesta,
    payload?.message,
    payload?.summary,
    payload?.summary_message,
    payload?.data?.summary,
    meta?.result_summary,
    responseMeta?.result_summary,
  ];

  return fragments
    .map(value => (typeof value === 'string' ? value : undefined))
    .filter((value): value is string => typeof value === 'string' && value.trim().length > 0);
};

const normalizeDecisionText = (value?: string) => canonicalizeText(value ?? '');

const normalizeForComparison = (message: OrchestratorMessage): string => {
  for (const fragment of gatherComparableStrings(message)) {
    const { cleaned } = splitDecisionSuffix(fragment);
    const canonical = canonicalizeText(cleaned || fragment);
    if (canonical) {
      return canonical;
    }
  }

  const fallback = `${message.role || ''}|${message.agent || ''}|${message.id || ''}|${message.content || ''}`;
  return canonicalizeText(fallback);
};

const sanitizeAgentMessage = (
  message: OrchestratorMessage,
): { sanitized: OrchestratorMessage; decisionText: string | null } => {
  const { cleaned, decision } = splitDecisionSuffix(message.content);
  const nextContent =
    typeof cleaned === 'string' && cleaned.trim().length > 0 ? cleaned : (message.content ?? '');
  const strippedQuestion = nextContent ? stripTrailingQuestion(nextContent) : nextContent;
  return {
    sanitized: { ...message, content: strippedQuestion },
    decisionText: decision,
  };
};

const isPendingAgentMessage = (message: OrchestratorMessage): boolean => {
  const payload = (message as any)?.payload ?? {};
  const meta = payload?.metadata ?? payload?.meta ?? payload?.response_metadata ?? {};
  return Boolean(
    meta?.el_cajas_pending ||
      meta?.requires_human_approval ||
      meta?.human_gate_pending ||
      payload?.el_cajas_pending ||
      payload?.requires_human_approval,
  );
};

const defaultSimulation = (startEventIndex: number): TurnSimulation => ({
  events: [],
  status: 'idle',
  collapsed: true,
  startEventIndex,
});

const toDecisionMessage = (message: OrchestratorMessage): OrchestratorMessage => {
  const payload = (message as any)?.payload ?? {};
  const candidateStrings: Array<string | undefined> = [
    payload?.response_metadata?.human_gate_result?.message,
    payload?.metadata?.human_gate_result?.message,
    payload?.message,
    message.content,
  ];

  const raw = candidateStrings.find(
    value => typeof value === 'string' && value.trim().length > 0,
  );

  if (!raw) {
    return { ...message };
  }

  const sentences = raw
    .split(/(?<=\.)\s+/)
    .map(sentence => sentence.trim())
    .filter(Boolean);

  const finalSentence = sentences.length > 0 ? sentences[sentences.length - 1] : raw.trim();
  const cleaned = finalSentence.replace(/\s+/g, ' ').trim();

  return {
    ...message,
    content: cleaned || (message.content ?? ''),
  };
};

const createDecisionFromText = (
  base: OrchestratorMessage,
  text: string,
  fallbackId: string,
): OrchestratorMessage => ({
  ...base,
  id: base.id ? `${base.id}-decision` : `${fallbackId}-decision`,
  role: 'agent',
  content: text,
});

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
    payload?.metadata,
  ];

  for (const container of planContainers) {
    if (!container || typeof container !== 'object') {
      continue;
    }

    const plan =
      container.reasoning_plan && typeof container.reasoning_plan === 'object'
        ? container.reasoning_plan
        : container;

>>>>>>> origin/develop
    const steps = (plan as Record<string, unknown>)?.steps;
    if (Array.isArray(steps) && steps.length > 0) {
      return steps as ReasoningPlanStep[];
    }
  }

  return [];
};

<<<<<<< HEAD
// Función eliminada - usando getActionType mejorado de chatHelpers

function SimpleChatBox({ sucursal, onRemoveSucursal }: ChatBoxProps) {
=======
const toBubbleMessage = (
  message: OrchestratorMessage | undefined,
  fallback: 'user' | 'bot',
) => {
  if (!message) {
    return null;
  }

  const sender = message.role === 'user' ? 'user' : fallback;

  const payload = (message as any)?.payload ?? {};
  const textCandidates = [
    typeof message.content === 'string' ? message.content : null,
    typeof payload.respuesta === 'string' ? payload.respuesta : null,
    typeof payload.message === 'string' ? payload.message : null,
    typeof (message as any)?.text === 'string' ? (message as any).text : null,
  ];

  const text =
    textCandidates.find(value => typeof value === 'string' && value.trim().length > 0)?.trim() ?? '';

  return {
    id: message.id || getMessageKey(message),
    sender,
    text,
    agent: message.agent,
    timestamp: message.timestamp || Date.now(),
  };
};

const buildTurns = (
  messages: OrchestratorMessage[],
  previousTurns: ChatTurn[],
  agentEventCount: number,
): ChatTurn[] => {
  const previousById = new Map(previousTurns.map(turn => [turn.id, turn]));
  const result: ChatTurn[] = [];
  let currentTurn: ChatTurn | null = null;
  let lastUserTurn: ChatTurn | null = null;

  const ensureTurn = (fallbackId: string, fallbackTimestamp?: number): ChatTurn => {
    if (currentTurn && currentTurn.id === fallbackId) {
      return currentTurn;
    }

    const existing = previousById.get(fallbackId);
    const simulation = existing
      ? { ...existing.simulation, events: [...existing.simulation.events] }
      : { ...defaultSimulation(agentEventCount), status: 'complete' as SimulationStatus };

    const userMessage =
      existing?.userMessage ??
      ({
        id: `${fallbackId}-user`,
        role: 'user',
        content: '',
        agent: 'system',
        timestamp: fallbackTimestamp ?? Date.now(),
      } as OrchestratorMessage);

    const turn: ChatTurn = existing
      ? {
          ...existing,
          userMessage,
          agentMessages: [...existing.agentMessages],
          decisions: [...existing.decisions],
          simulation,
        }
      : {
          id: fallbackId,
          userMessage,
          agentMessages: [],
          decisions: [],
          simulation,
        };

    result.push(turn);
    currentTurn = turn;
    return turn;
  };

  const addAgentMessage = (turn: ChatTurn, agentMessage: OrchestratorMessage) => {
    const normalized = normalizeForComparison(agentMessage);
    const pendingIncoming = isPendingAgentMessage(agentMessage);

    if (pendingIncoming) {
      const existingPendingIndex = turn.agentMessages.findIndex(
        existing =>
          existing.agent === agentMessage.agent &&
          isPendingAgentMessage(existing),
      );
      if (existingPendingIndex >= 0) {
        const updatedMessages = [...turn.agentMessages];
        updatedMessages[existingPendingIndex] = { ...agentMessage, role: 'agent' };
        turn.agentMessages = updatedMessages;
        return;
      }
    }

    const pendingIndex = turn.agentMessages.findIndex(
      existing =>
        existing.agent === agentMessage.agent &&
        isPendingAgentMessage(existing) &&
        !isPendingAgentMessage(agentMessage),
    );

    if (pendingIndex >= 0) {
      const updatedMessages = [...turn.agentMessages];
      updatedMessages[pendingIndex] = { ...agentMessage, role: 'agent' };
      turn.agentMessages = updatedMessages;
      return;
    }

    const alreadyExists = turn.agentMessages.some(
      existing => normalizeForComparison(existing) === normalized,
    );
    if (alreadyExists) {
      turn.agentMessages = turn.agentMessages.map(existing =>
        normalizeForComparison(existing) === normalized ? { ...existing, ...agentMessage } : existing,
      );
      return;
    }

    turn.agentMessages = [...turn.agentMessages, { ...agentMessage, role: 'agent' }];
  };

  const addDecisionMessage = (turn: ChatTurn, decisionMessage: OrchestratorMessage) => {
    const normalized = normalizeDecisionText(decisionMessage.content);
    if (!normalized) {
      return;
    }
    const alreadyExists = turn.decisions.some(
      existing => normalizeDecisionText(existing.content) === normalized,
    );
    if (!alreadyExists) {
      turn.decisions = [...turn.decisions, { ...decisionMessage, role: 'agent' }];
    }
  };

  messages.forEach((message, index) => {
    const role = message.role ?? (message.sender === 'user' ? 'user' : 'agent');

    if (role === 'user') {
      const turnId = message.id ?? `turn-${index}`;
      const existing = previousById.get(turnId);
      const simulation = existing
        ? { ...existing.simulation, events: [...existing.simulation.events] }
        : defaultSimulation(agentEventCount);

      const turn: ChatTurn = existing
        ? {
            ...existing,
            userMessage: message,
            agentMessages: [...existing.agentMessages],
            decisions: [...existing.decisions],
            simulation,
          }
        : {
            id: turnId,
            userMessage: message,
            agentMessages: [],
            decisions: [],
            simulation,
          };

      result.push(turn);
      currentTurn = turn;
      lastUserTurn = turn;
      return;
    }

    if (role !== 'agent' && role !== 'system') {
      return;
    }

    const fallbackId = message.id ?? `orphan-${index}`;
    const turn =
      lastUserTurn && lastUserTurn.userMessage?.role === 'user'
        ? lastUserTurn
        : ensureTurn(fallbackId, message.timestamp);
    currentTurn = turn;

    const payload = (message as any)?.payload ?? {};
    const isDecision =
      payload?.source === 'human_decision' ||
      payload?.response_metadata?.human_gate_result ||
      payload?.metadata?.human_gate_result;

    if (isDecision) {
      const decisionMessage = toDecisionMessage(message);
      addDecisionMessage(turn, decisionMessage);
      return;
    }

    if (role !== 'agent' && role !== 'system') {
      return;
    }

    const { sanitized, decisionText } = sanitizeAgentMessage(message);
    if ((sanitized.content && sanitized.content.trim().length > 0) || sanitized.payload) {
      addAgentMessage(turn, sanitized);
    }

    if (decisionText) {
      addDecisionMessage(turn, createDecisionFromText(sanitized, decisionText, fallbackId));
    }
  });

  return result;
};

const SimpleChatBox = ({ sucursal, onRemoveSucursal }: ChatBoxProps) => {
>>>>>>> origin/develop
  const {
    messages,
    loading,
    sendCommand,
    pendingActions,
    approvalReason,
    submitAction,
    appendLocalMessage,
    activeSessionId,
<<<<<<< HEAD
    agentEvents,  // Eventos directos del WebSocket de agentes
  } = useGlobalChat();

  const feedRef = useRef<HTMLDivElement>(null);

  // Ref para mantener estado actualizado y evitar stale closures
  const messagesRef = useRef(messages);
=======
    agentEvents,
  } = useGlobalChat();

  const feedRef = useRef<HTMLDivElement>(null);
  const messagesRef = useRef(messages);
  const activeSimulationRef = useRef<string | null>(null);

  const [turns, setTurns] = useState<ChatTurn[]>([]);

>>>>>>> origin/develop
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

<<<<<<< HEAD
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
=======
const sessionAgentEvents = useMemo(() => {
  if (!agentEvents || agentEvents.length === 0) {
    return [] as AgentEvent[];
  }

  const targetSession = (activeSessionId ?? 'global').toLowerCase();

  const normalizeSessionId = (value: string | null | undefined) => {
    if (!value) return 'global';
    return value.toLowerCase().replace(/^session[_-]?/, '');
  };

  return agentEvents.filter(event => {
    const rawSession =
      event?.session_id ??
      event?.data?.session_id ??
      event?.meta?.session_id ??
      null;

    if (!rawSession) {
      return normalizeSessionId(targetSession) === 'global';
    }

    return normalizeSessionId(rawSession) === normalizeSessionId(targetSession);
  });
}, [agentEvents, activeSessionId]);

useEffect(() => {
  chatLogger.debug('sessionAgentEvents updated', {
      count: sessionAgentEvents.length,
      sample: sessionAgentEvents[0],
    });
  }, [sessionAgentEvents]);

  useEffect(() => {
    setTurns(prev => buildTurns(messages, prev, sessionAgentEvents.length));
  }, [messages, sessionAgentEvents.length]);

  const {
    simState,
    startMorphingSequence,
    simulateEventStreaming,
    simulatePlanSteps,
    simulateCustomEvents,
    handleBatchComplete,
    resetForNewMessage,
    stopWaiting,
  } = useEventSimulation();

  const activeTurn = useMemo(() => {
    for (let index = turns.length - 1; index >= 0; index -= 1) {
      const turn = turns[index];
      if (turn.agentMessages.length === 0) {
        return turn;
      }

      if (turn.simulation.status !== 'complete') {
        return turn;
      }
    }

    return undefined;
  }, [turns]);

  const activeTurnId = activeTurn?.id;

  useEffect(() => {
    if (!activeTurn || activeTurn.agentMessages.length === 0) {
      return;
    }

    if (simState.simulatedEvents.length === 0) {
      return;
    }

    setTurns(prev =>
      prev.map(turn =>
        turn.id === activeTurn.id
          ? {
              ...turn,
              simulation: {
                ...turn.simulation,
                events: simState.simulatedEvents.map(event => ({ ...event })),
              },
            }
          : turn,
      ),
    );
  }, [simState.simulatedEvents, activeTurn?.id, activeTurn?.agentMessages.length]);

  useEffect(() => {
    if (!activeTurn || activeTurn.agentMessages.length === 0) {
      return;
    }

    if (activeTurn.simulation.status === 'complete') {
      return;
    }

    if (activeSimulationRef.current === activeTurn.id) {
      return;
    }

    const relevantAgentEvents = sessionAgentEvents.slice(activeTurn.simulation.startEventIndex);
    const finalMessage = activeTurn.agentMessages[0];
    const currentMessages = messagesRef.current;

    let planSteps: ReasoningPlanStep[] = [];
    for (
      let index = currentMessages.length - 1;
      index >= Math.max(0, currentMessages.length - 10);
      index -= 1
    ) {
      const candidate = extractReasoningPlanSteps(currentMessages[index] as MessageWithPayload);
      if (candidate.length > 0) {
        planSteps = candidate;
        break;
      }
    }

    setTurns(prev =>
      prev.map(turn =>
        turn.id === activeTurn.id
          ? {
              ...turn,
              simulation: {
                ...turn.simulation,
                status: 'running',
              },
            }
          : turn,
      ),
    );

    activeSimulationRef.current = activeTurn.id;

    const queryText =
      activeTurn.userMessage.content ??
      (typeof (activeTurn.userMessage as any)?.text === 'string'
        ? (activeTurn.userMessage as any).text
        : '');

    const taskEvents = buildAgentTaskEvents({
      agentEvents: relevantAgentEvents,
      planSteps,
      finalMessage,
    });

    stopWaiting();

    let simulationDuration = 0;

    if (taskEvents.length > 0) {
      simulationDuration = simulateCustomEvents(taskEvents);
    } else if (relevantAgentEvents.length > 0) {
      simulationDuration = simulateEventStreaming(relevantAgentEvents, queryText ?? '');
    } else if (planSteps.length > 0) {
      simulationDuration = simulatePlanSteps(planSteps);
    } else {
      handleBatchComplete();
      setTurns(prev =>
        prev.map(turn =>
          turn.id === activeTurn.id
            ? {
                ...turn,
                simulation: {
                  ...turn.simulation,
                  status: 'complete',
                },
              }
            : turn,
        ),
      );
      activeSimulationRef.current = null;
      return;
    }

    let finalizeTimer: ReturnType<typeof setTimeout> | undefined;

    const finalize = () => {
      handleBatchComplete();
      setTurns(prev =>
        prev.map(turn =>
          turn.id === activeTurn.id
            ? {
                ...turn,
                simulation: {
                  ...turn.simulation,
                  status: 'complete',
                },
              }
            : turn,
        ),
      );
      activeSimulationRef.current = null;
    };

    if (simulationDuration > 0) {
      const finalDelay =
        simulationDuration +
        ANIMATION_CONFIG.timings.shimmerDuration +
        ANIMATION_CONFIG.timings.finalDisplay;

      finalizeTimer = window.setTimeout(finalize, finalDelay);
    } else {
      finalize();
    }

    return () => {
      if (finalizeTimer) {
        clearTimeout(finalizeTimer);
      }

      if (activeSimulationRef.current === activeTurn.id) {
        activeSimulationRef.current = null;
      }
    };
  }, [
    activeTurn?.id,
    activeTurn?.agentMessages.length,
    activeTurn?.simulation.status,
    activeTurn?.simulation.startEventIndex,
    sessionAgentEvents,
    simulateCustomEvents,
    simulateEventStreaming,
    simulatePlanSteps,
    handleBatchComplete,
    stopWaiting,
  ]);

  useEffect(() => {
    if (feedRef.current) {
      feedRef.current.scrollTop = feedRef.current.scrollHeight;
    }
  }, [turns, simState.simulatedEvents, simState.morphingText, simState.morphingPhase]);

  const handleToggleSimulation = useCallback(
    (turnId: string) => {
      setTurns(prev =>
        prev.map(turn => {
          if (turn.id !== turnId) {
            return turn;
          }

          const isActive = turn.id === activeTurnId;
          if (isActive && turn.simulation.status === 'running') {
            return turn;
          }

          return {
            ...turn,
            simulation: {
              ...turn.simulation,
              collapsed: !turn.simulation.collapsed,
            },
          };
        }),
      );
    },
    [activeTurnId],
  );

  const handleSendMessage = useCallback(
    async (text: string) => {
      if (!text.trim()) return;

      chatLogger.info('Enviando mensaje', { text });

      try {
        activeSimulationRef.current = null;
        resetForNewMessage(text);
        startMorphingSequence();
        await sendCommand(text);
      } catch (error) {
        chatLogger.error('Error al enviar mensaje', { error, text });
      }
    },
    [sendCommand, startMorphingSequence, resetForNewMessage],
  );

  const {
    beginVoiceRecording,
    finishVoiceRecording,
    isRecording,
    isProcessing,
    isMicPressed,
    voiceNotice,
    partialTranscript,
    autoPlayError,
    audioUrl,
    isAudioMuted,
    isAudioPlaying,
    handleToggleMute,
    handleReplay,
    handleStopPlayback,
  } = useVoiceInterface({
    sessionId: activeSessionId ?? 'global',
    onMessageAppend: (entry: { content?: string; role?: string; metadata?: Record<string, any> } | null) => {
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

  const handlePressStart = useCallback(
    (event: MouseEvent<HTMLButtonElement> | TouchEvent<HTMLButtonElement>) => {
      event.preventDefault();
      beginVoiceRecording();
    },
    [beginVoiceRecording],
  );

  const handlePressEnd = useCallback(
    (event: MouseEvent<HTMLButtonElement> | TouchEvent<HTMLButtonElement>) => {
      event.preventDefault();
      finishVoiceRecording();
    },
    [finishVoiceRecording],
  );

  const handleSubmitAction = useCallback(
    async (params: Parameters<typeof submitAction>[0]) => {
      await submitAction(params);
    },
    [submitAction],
  );
>>>>>>> origin/develop

  // Renderizar mensajes regulares (no eventos)
  return (
<<<<<<< HEAD
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
=======
    <div className={styles.container}>
      <div ref={feedRef} className={styles.feed} role="log" aria-live="polite">
        {sucursal && (
          <div className={styles.sucursalCard}>
            <span>Sucursal: {sucursal.name}</span>
            {onRemoveSucursal && (
              <button onClick={onRemoveSucursal} type="button">
>>>>>>> origin/develop
                Quitar
              </button>
            )}
          </div>
        )}
<<<<<<< HEAD

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
        {simState.simulatedEvents.map((event, idx) => {
          if (event.status === 'pending') return null;

          const showHeader =
            idx === 0 ||
            (idx > 0 && simState.simulatedEvents[idx - 1].agent !== event.agent);

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
        })}
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
=======

        {turns.map(turn => (
          <TurnBlock
            key={turn.id}
            turn={turn}
            onToggle={handleToggleSimulation}
            isActive={turn.id === activeTurnId}
            liveEvents={turn.id === activeTurnId ? simState.simulatedEvents : []}
            morphingText={turn.id === activeTurnId ? simState.morphingText : undefined}
            morphingPhase={turn.id === activeTurnId ? simState.morphingPhase : undefined}
            morphingKey={turn.id === activeTurnId ? simState.morphingKey : undefined}
          />
        ))}
      </div>

      {pendingActions.length > 0 && (
        <PendingActions
          pendingActions={pendingActions}
          approvalReason={approvalReason}
          onSubmitAction={handleSubmitAction}
          loading={loading}
        />
      )}

      {(voiceNotice || partialTranscript || autoPlayError) && (
        <div className={styles.voiceStatus}>
        {voiceNotice && <span className={styles.voiceNotice}>{voiceNotice}</span>}
        {partialTranscript && (
          <span className={styles.voicePartial}>{partialTranscript}</span>
        )}
        {autoPlayError && <span className={styles.voiceError}>{autoPlayError}</span>}
      </div>
    )}

      {(audioUrl || isRecording || isProcessing) && (
        <div className={styles.voiceControls}>
          {audioUrl && (
            <div
              className={
                isAudioPlaying ? styles.voiceAudioPreviewPlaying : styles.voiceAudioPreview
              }
            >
              <span className={styles.voicePreviewLabel}>Sintetizado</span>
              <button
                type="button"
                className={`${styles.voiceControlButton} ${isAudioMuted ? styles.voiceControlButtonMuted : ''}`}
                onClick={handleToggleMute}
              >
                {isAudioMuted ? 'Audio OFF' : 'Audio ON'}
              </button>
              <div className={styles.voicePlayback}>
                <button
                  type="button"
                  className={styles.voiceControlButton}
                  onClick={handleReplay}
                >
                  Reproducir
                </button>
                <button
                  type="button"
                  className={styles.voiceControlButton}
                  onClick={handleStopPlayback}
                  disabled={!isAudioPlaying}
                >
                  Detener
                </button>
              </div>
            </div>
          )}
          {!audioUrl && (isRecording || isProcessing) && (
            <span className={styles.voiceCaptureState}>
              {isRecording ? 'Grabando…' : 'Procesando voz…'}
            </span>
          )}
        </div>
      )}

      <ChatInput
        onSend={handleSendMessage}
        loading={loading}
        rightSlot={
          <button
            className={`${styles.micButton} ${isMicPressed ? styles.pressed : ''} ${
              isRecording ? styles.recording : ''
            }`}
            onMouseDown={handlePressStart}
            onMouseUp={handlePressEnd}
            onTouchStart={handlePressStart}
            onTouchEnd={handlePressEnd}
            title="Mantén presionado para grabar"
            disabled={loading || isProcessing}
            aria-label={isRecording ? 'Grabando voz' : 'Mantén presionado para grabar'}
            aria-pressed={isMicPressed}
            type="button"
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
>>>>>>> origin/develop
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
};

<<<<<<< HEAD
// Exportar con memo para optimizar re-renders
// Solo re-renderiza si cambia sucursal o onRemoveSucursal
=======
const TurnBlock = memo(
  ({
    turn,
    onToggle,
    isActive,
    liveEvents,
    morphingText,
    morphingPhase,
    morphingKey,
  }: TurnBlockProps) => {
    const userBubble = toBubbleMessage(turn.userMessage, 'user');
    const agentBubbles = turn.agentMessages
      .map(message => toBubbleMessage(message, 'bot'))
      .filter(Boolean);
    const decisionBubbles = turn.decisions
      .map(message => toBubbleMessage(message, 'bot'))
      .filter(Boolean);
    const events =
      isActive && turn.simulation.status !== 'complete' ? liveEvents : turn.simulation.events;
    const collapsed =
      isActive && turn.simulation.status === 'running'
        ? false
        : Boolean(turn.simulation.collapsed);
    const showMorphing = isActive && turn.simulation.status === 'running' && morphingText && morphingPhase;
    const showTimeline = events.length > 0;

    const contentId = `${turn.id}-workflow`;

    return (
      <div className={styles.turnBlock}>
        {userBubble && (
          <MessageBubble
            message={{
              id: userBubble.id,
              sender: userBubble.sender,
              text: userBubble.text,
              agent: userBubble.agent,
              timestamp: userBubble.timestamp,
            }}
          />
        )}

        <section className={styles.simulationSection} aria-labelledby={`${contentId}-label`}>
          <button
            type="button"
            className={styles.simulationBanner}
            onClick={() => onToggle(turn.id)}
            aria-expanded={!collapsed}
            aria-controls={contentId}
            disabled={isActive && turn.simulation.status === 'running'}
          >
            <span id={`${contentId}-label`} className={styles.simulationLabel}>
              Workflow
            </span>
            <span className={styles.simulationGlow} aria-hidden="true" />
          </button>

          <div
            id={contentId}
            className={
              collapsed
                ? styles.simulationContentCollapsed
                : styles.simulationContent
            }
          >
            {showMorphing && morphingText && morphingPhase && (
              <div className={styles.morphingWrapper}>
                <span
                  key={morphingKey}
                  className={getMorphingClasses(styles, morphingPhase)}
                >
                  {morphingText}
                </span>
                <div className={styles.processingIndicator}>
                  <span className={styles.processingDot} />
                  <span className={styles.processingDot} />
                  <span className={styles.processingDot} />
                </div>
              </div>
            )}

            {showTimeline && (
              <div className={styles.simulationTimeline}>
                {events.map((event, index) => {
                  if (event.status === 'pending') {
                    return null;
                  }

                  const showHeader =
                    index === 0 ||
                    (index > 0 && events[index - 1].agent !== event.agent);

                  const { containerClass, bulletClass, textClass } = getEventClasses(
                    styles,
                    event.status,
                  );

                  return (
                    <div key={event.id} className={styles.timelineEntry}>
                      {showHeader && (
                        <div className={styles.agentHeader}>
                          {event.friendlyName || getFriendlyAgentName(event.agent)}
                        </div>
                      )}
                      <div className={containerClass}>
                        <div className={bulletClass} />
                        <div className={styles.eventBody}>
                          <span className={textClass}>{event.primaryText}</span>
                          {event.detail && (
                            <span className={styles.eventDetail}>{event.detail}</span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {agentBubbles.map((bubble, index) => (
          <MessageBubble
            key={`${bubble!.id}-${index}`}
            message={{
              id: bubble!.id,
              sender: bubble!.sender,
              text: bubble!.text,
              agent: bubble!.agent,
              timestamp: bubble!.timestamp,
            }}
          />
        ))}

        {decisionBubbles.map((bubble, index) => (
          <MessageBubble
            key={`${bubble!.id}-decision-${index}`}
            message={{
              id: bubble!.id,
              sender: bubble!.sender,
              text: bubble!.text,
              agent: bubble!.agent,
              timestamp: bubble!.timestamp,
            }}
          />
        ))}
      </div>
    );
  },
);

TurnBlock.displayName = 'TurnBlock';

>>>>>>> origin/develop
export default memo(SimpleChatBox, (prevProps, nextProps) => {
  return (
    prevProps.sucursal === nextProps.sucursal &&
    prevProps.onRemoveSucursal === nextProps.onRemoveSucursal
  );
});
<<<<<<< HEAD


=======
>>>>>>> origin/develop
