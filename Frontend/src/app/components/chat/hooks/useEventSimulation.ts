import { useCallback, useRef, useReducer, useEffect } from 'react';
import { Message } from '@/app/types/chat';
import {
  filterAgentEvents,
  getEventPayload,
  getAgentName,
  getFriendlyAgentName,
  getActionType,
  TimerManager,
  simulationReducer,
  initialSimulationState,
  type SimulatedEvent,
  type ReasoningPlanStep
} from '@/app/utils/chatHelpers';
import { getContextualMessages } from '@/app/config/agentMessages';
import { ANIMATION_CONFIG, getOrchestratorSequence } from '../../../config/morphingConfig';
import { chatLogger } from '@/app/utils/ChatBoxLogger';

const SHIMMER_START_DELAY = 120;

const pickFirstString = (values: unknown[]): string | undefined => {
  for (const value of values) {
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed.length > 0) {
        return trimmed;
      }
    }
  }
  return undefined;
};

/**
 * Custom hook para manejar la simulación de eventos del chat
 * Centraliza toda la lógica de morphing y simulación de eventos
 */
export function useEventSimulation() {
  const [simState, dispatch] = useReducer(simulationReducer, initialSimulationState);
  const timerManager = useRef(new TimerManager());
  const stateRef = useRef(simState);

  /**
   * CAMBIO CRÍTICO: Mantenemos una ref sincronizada con el estado
   * para evitar problemas de stale closure en callbacks asíncronos.
   * Esto garantiza que siempre tengamos el estado más reciente
   * cuando los timers se ejecutan.
   */
  useEffect(() => {
    stateRef.current = simState;
  }, [simState]);

  const scheduleSimulatedEvents = useCallback((simEvents: SimulatedEvent[]): number => {
    timerManager.current.clearAll();

    if (simEvents.length === 0) {
      dispatch({ type: 'SET_EVENTS', payload: [] });
      dispatch({ type: 'COMPLETE_SIMULATION' });
      return 0;
    }

    dispatch({ type: 'SET_EVENTS', payload: simEvents });

    const eventActiveDuration = ANIMATION_CONFIG.timings.shimmerDuration * 2;
    const betweenEvents = ANIMATION_CONFIG.timings.betweenEvents;

    const runEvent = (eventIndex: number) => {
      dispatch({ type: 'SET_EVENT_INDEX', payload: eventIndex });
      dispatch({
        type: 'UPDATE_EVENT',
        payload: { index: eventIndex, update: { status: 'active' } }
      });

      timerManager.current.set(
        `complete-${eventIndex}`,
        () => {
          dispatch({
            type: 'UPDATE_EVENT',
            payload: { index: eventIndex, update: { status: 'completed' } }
          });

          if (eventIndex + 1 < simEvents.length) {
            timerManager.current.set(
              `start-${eventIndex + 1}`,
              () => runEvent(eventIndex + 1),
              betweenEvents
            );
          } else {
            dispatch({ type: 'COMPLETE_SIMULATION' });
          }
        },
        eventActiveDuration
      );
    };

    timerManager.current.set('start-0', () => runEvent(0), SHIMMER_START_DELAY);

    const totalDuration =
      simEvents.length * eventActiveDuration + Math.max(simEvents.length - 1, 0) * betweenEvents;
    return totalDuration;
  }, []);

  const simulateEventStreaming = useCallback((batchedEvents: Message[], query: string): number => {
    chatLogger.debug('Simulando eventos', { totalEvents: batchedEvents.length, query });

    const agentEvents = filterAgentEvents(batchedEvents);
    chatLogger.debug('Eventos de agentes filtrados', { count: agentEvents.length });

    if (agentEvents.length === 0) {
      return scheduleSimulatedEvents([]);
    }

    const now = Date.now();

    const simEvents: SimulatedEvent[] = agentEvents.map((msg, idx) => {
      const agent = getAgentName(msg);
      const friendlyName = getFriendlyAgentName(agent);
      const actionType = getActionType(msg);
      const payload = getEventPayload(msg) as any;
      const eventEnvelope = payload?.event ?? {};
      const envelopeData = eventEnvelope?.data ?? {};
      const envelopeMeta = eventEnvelope?.meta ?? {};

      // Extraer texto real del evento - priorizar content de meta (desde realtime_event_bus)
      const primaryText =
        pickFirstString([
          envelopeMeta?.content,      // Content from realtime_event_bus.py
          envelopeData?.content,      // Alternative content location
          msg?.meta?.content,         // Direct from AgentEvent
          msg?.data?.content,         // Alternative from AgentEvent
          payload?.content,            // Direct content
          payload?.summary,
          payload?.message,
          payload?.text,
          msg.content,
          msg.text,
          envelopeData?.summary,
          envelopeData?.message,
          envelopeData?.text,
          envelopeMeta?.summary,
          envelopeMeta?.message,
          envelopeMeta?.text
        ]) ??
        `${friendlyName || agent || 'Agente'} procesando...`;  // NO usar getContextualMessages - solo fallback mínimo
      chatLogger.debug('Procesando agente', {
        agent,
        actionType,
        primaryText
      });

      return {
        id: msg.id || `sim-${idx}-${now}`,
        agent,
        friendlyName,
        primaryText,
        status: 'pending'
      };
    });

    return scheduleSimulatedEvents(simEvents);
  }, [scheduleSimulatedEvents]);

  const simulateCustomEvents = useCallback((events: SimulatedEvent[]): number => {
    if (!Array.isArray(events) || events.length === 0) {
      return scheduleSimulatedEvents([]);
    }
    return scheduleSimulatedEvents(events);
  }, [scheduleSimulatedEvents]);

  const simulatePlanSteps = useCallback((steps: ReasoningPlanStep[]): number => {
    chatLogger.debug('Simulando plan razonado', { steps: steps.length });

    if (!steps || steps.length === 0) {
      return scheduleSimulatedEvents([]);
    }

    const now = Date.now();

    const simEvents: SimulatedEvent[] = steps.map((step, idx) => {
      const primaryCandidate = pickFirstString([step.title, step.description, step.expected_output]) ?? `Paso ${idx + 1}`;
      const trimmedPrimary = primaryCandidate.trim();

      const agentValue = step.agent && step.agent.trim() ? step.agent : 'planificador';
      const friendlyName = getFriendlyAgentName(agentValue);

      return {
        id: step.id || `plan-${idx}-${now}`,
        agent: agentValue,
        friendlyName,
        primaryText: trimmedPrimary,
        status: 'pending'
      };
    });

    return scheduleSimulatedEvents(simEvents);
  }, [scheduleSimulatedEvents]);

  const startMorphingSequence = useCallback((useRandomPhrases: boolean = false) => {
    chatLogger.debug('Iniciando morphing sequence', { randomized: useRandomPhrases });
    let sequenceIndex = 0;

    const sequence = getOrchestratorSequence(useRandomPhrases);

    const runMorphing = () => {
      if (sequenceIndex < sequence.length) {
        dispatch({
          type: 'SET_MORPHING',
          payload: {
            text: sequence[sequenceIndex],
            phase: 'shimmer',
            incrementKey: true
          }
        });

        timerManager.current.set(
          'morphing',
          () => {
            sequenceIndex += 1;
            if (sequenceIndex < sequence.length) {
              runMorphing();
            } else {
              dispatch({
                type: 'SET_MORPHING',
                payload: {
                  text: sequence[sequence.length - 1],
                  phase: 'waiting',
                  incrementKey: true
                }
              });
              chatLogger.debug('Morphing en fase waiting');
            }
          },
          ANIMATION_CONFIG.timings.betweenWords
        );
      }
    };

    runMorphing();
  }, []);

  const handleBatchComplete = useCallback(
    (appendMessage?: (msg: any) => void, currentMorphingText?: string) => {
      chatLogger.debug('Batch completo, finalizando morphing');

      // Use a ref to get the latest morphing text
      const stateSnapshot = stateRef.current;
      const textToPersist = currentMorphingText || stateSnapshot.morphingText;

      dispatch({
        type: 'SET_MORPHING',
        payload: {
          text: textToPersist,
          phase: 'final',
          incrementKey: true
        }
      });

      if (appendMessage && textToPersist) {
        timerManager.current.set(
          'persistOrchestrator',
          () => {
            appendMessage({
              id: `orchestrator-${Date.now()}`,
              role: 'agent',
              content: textToPersist,
              agent: 'orchestrator'
            });
            dispatch({ type: 'CLEAR_MORPHING' });
          },
          ANIMATION_CONFIG.timings.finalDisplay
        );
      } else {
        timerManager.current.set(
          'clearMorphing',
          () => {
            dispatch({ type: 'CLEAR_MORPHING' });
          },
          ANIMATION_CONFIG.timings.finalDisplay
        );
      }
    },
    [] // No dependencies needed since we use stateRef
  );

  const resetForNewMessage = useCallback((text: string) => {
    timerManager.current.clearAll();
    dispatch({ type: 'RESET_FOR_NEW_MESSAGE', payload: text });
  }, []);

  const stopWaiting = useCallback(() => {
    dispatch({ type: 'STOP_WAITING' });
  }, []);

  useEffect(() => {
    return () => {
      timerManager.current.clearAll();
    };
  }, []);

  return {
    simState,
    simulateEventStreaming,
    simulatePlanSteps,
    simulateCustomEvents,
    startMorphingSequence,
    handleBatchComplete,
    resetForNewMessage,
    stopWaiting,
    timerManager: timerManager.current
  };
}





