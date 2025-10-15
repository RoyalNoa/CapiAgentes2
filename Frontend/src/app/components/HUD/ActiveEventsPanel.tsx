/**
 * Ruta: Frontend/src/app/components/HUD/ActiveEventsPanel.tsx
 * Descripción: Muestra el workflow más reciente con el mismo estilo de la vista de chat.
 * Estado: Activo
 */

'use client';

import React, { useMemo } from 'react';
import styles from './ActiveEventsPanel.module.css';
import chatStyles from '../chat/SimpleChatBox.module.css';
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';
import {
  buildAgentTaskEvents,
  extractReasoningPlanStepsFromMessage,
  getEventClasses,
  getFriendlyAgentName,
  type ReasoningPlanStep,
  type SimulatedEvent,
} from '@/app/utils/chatHelpers';
import type { AgentEvent } from '@/app/hooks/useAgentWebSocket';
import type { OrchestratorMessage } from '@/app/utils/orchestrator/useOrchestratorChat';

interface Event {
  id: string;
  type: string;
  timestamp: string;
  data?: Record<string, unknown>;
  agent?: string;
}

interface ActiveEventsPanelProps {
  events: Event[];
  isConnected: boolean;
}

const normalizeSessionId = (value: string | null | undefined) => {
  if (!value) {
    return 'global';
  }
  return value.toLowerCase().replace(/^session[_-]?/, '');
};

const pickFinalAgentMessage = (messages: OrchestratorMessage[]): OrchestratorMessage | undefined => {
  for (let index = messages.length - 1; index >= 0; index -= 1) {
    const message = messages[index];
    if (!message) {
      continue;
    }
    const role = message.role ?? ((message as unknown as { sender?: string })?.sender ?? 'agent');
    if (role !== 'agent') {
      continue;
    }
    const payload = (message as any)?.payload ?? {};
    const hasContent =
      (typeof message.content === 'string' && message.content.trim().length > 0) ||
      typeof (payload?.respuesta ?? payload?.message ?? payload?.response) === 'string';
    if (hasContent || Object.keys(payload ?? {}).length > 0) {
      return message;
    }
  }
  return undefined;
};

export const ActiveEventsPanel: React.FC<ActiveEventsPanelProps> = ({
  events: _events,
  isConnected,
}) => {
  const { messages, agentEvents, activeSessionId } = useGlobalChat();

  const typedMessages = (messages ?? []) as OrchestratorMessage[];

  const sessionAgentEvents = useMemo<AgentEvent[]>(() => {
    if (!agentEvents || agentEvents.length === 0) {
      return [];
    }

    const targetSession = normalizeSessionId(activeSessionId ?? 'global');

    return agentEvents.filter(event => {
      const rawSession =
        (event as any)?.session_id ??
        (event as any)?.data?.session_id ??
        (event as any)?.meta?.session_id ??
        null;

      if (!rawSession) {
        return targetSession === 'global';
      }

      return normalizeSessionId(String(rawSession)) === targetSession;
    });
  }, [agentEvents, activeSessionId]);

  const planSteps = useMemo<ReasoningPlanStep[]>(() => {
    if (!typedMessages || typedMessages.length === 0) {
      return [];
    }

    for (
      let index = typedMessages.length - 1;
      index >= Math.max(0, typedMessages.length - 10);
      index -= 1
    ) {
      const candidate = extractReasoningPlanStepsFromMessage(typedMessages[index] as any);
      if (candidate.length > 0) {
        return candidate;
      }
    }

    return [];
  }, [typedMessages]);

  const finalMessage = useMemo<OrchestratorMessage | undefined>(() => {
    if (!typedMessages || typedMessages.length === 0) {
      return undefined;
    }
    return pickFinalAgentMessage(typedMessages);
  }, [typedMessages]);

  const workflowEvents = useMemo<SimulatedEvent[]>(() => {
    const timeline = buildAgentTaskEvents({
      agentEvents: sessionAgentEvents,
      planSteps,
      finalMessage,
    });

    if (!timeline || timeline.length === 0) {
      return [];
    }

    return timeline.map((event, index) => {
      const normalizedStatus: SimulatedEvent['status'] =
        event.status === 'active'
          ? 'active'
          : event.status === 'completed'
            ? 'completed'
            : 'completed';

      return {
        ...event,
        id: event.id ?? `workflow-event-${index}`,
        status: normalizedStatus,
      };
    });
  }, [sessionAgentEvents, planSteps, finalMessage]);

  const workflowLabel = useMemo(() => {
    if (!finalMessage?.agent) {
      return 'Última ejecución';
    }
    return getFriendlyAgentName(finalMessage.agent);
  }, [finalMessage?.agent]);

  return (
    <div className={styles.container}>
      <div className={styles.headerRow}>
        <div className={styles.titleBlock}>
          <span className={styles.title}>Workflow</span>
          <span className={styles.subtitle}>{workflowLabel}</span>
        </div>
        <div className={styles.connectionBadge} data-connected={isConnected ? 'true' : 'false'}>
          {isConnected ? 'LIVE' : 'OFFLINE'}
        </div>
      </div>

      <div className={`${chatStyles.simulationContent} ${styles.timelineSurface}`}>
        {workflowEvents.length === 0 ? (
          <div className={styles.emptyState}>
            <span>Sin workflow activo</span>
            <span>Interactúa en el chat para generar uno nuevo.</span>
          </div>
        ) : (
          <div className={`${chatStyles.simulationTimeline} ${styles.timelineContent}`}>
            {workflowEvents.map((event, index) => {
              const previous = workflowEvents[index - 1];
              const showHeader = index === 0 || (previous && previous.agent !== event.agent);
              const friendlyName = event.friendlyName || getFriendlyAgentName(event.agent);
              const { containerClass, bulletClass, textClass } = getEventClasses(chatStyles, event.status);

              return (
                <div key={event.id} className={chatStyles.timelineEntry}>
                  {showHeader ? <div className={chatStyles.agentHeader}>{friendlyName}</div> : null}
                  <div className={containerClass}>
                    <div className={bulletClass} />
                    <div className={chatStyles.eventBody}>
                      <div className={`${chatStyles.eventSummary} ${textClass}`}>{event.primaryText}</div>
                      {event.detail ? <div className={chatStyles.eventDetail}>{event.detail}</div> : null}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default ActiveEventsPanel;
