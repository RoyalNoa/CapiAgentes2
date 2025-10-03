'use client';

import React, {
  createContext,
  useContext,
  useState,
  ReactNode,
  useCallback,
  useEffect,
  useRef,
} from 'react';
import useOrchestratorChat, { OrchestratorMessage, PendingAction, SubmitActionParams } from '@/app/utils/orchestrator/useOrchestratorChat';
import { useAgentWebSocket, AgentEvent } from '@/app/hooks/useAgentWebSocket';
import { API_BASE } from '@/app/utils/orchestrator/client';

interface GlobalChatContextType {
  // Chat state
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;

  // Orchestrator integration - pass through all hook functionality
  messages: any[];
  loading: boolean;
  summary?: any;
  anomalies?: any[];
  dashboard?: any;
  pendingActions: PendingAction[];
  approvalReason: string | null;
  sendCommand: (text: string) => Promise<void>;
  submitAction: (params: SubmitActionParams) => Promise<void>;
  connection: { status: 'idle' | 'connecting' | 'open' | 'reconnecting' | 'failed' | 'closed' };
  appendLocalMessage: (message: OrchestratorMessage) => void;

  activeSessionId: string;
  sessionIds: string[];
  createNewSession: () => Promise<string>;
  switchSession: (sessionId: string) => void;
  refreshSessions: () => Promise<void>;


  // Sucursal state (from maps integration)
  selectedSucursal: any;
  setSelectedSucursal: (sucursal: any) => void;

  // Layout customization
  chatWidth: number;
  setChatWidth: (width: number) => void;
  chatPosition: 'left' | 'right';
  setChatPosition: (position: 'left' | 'right') => void;
  showSidebar: boolean;
  setShowSidebar: (show: boolean) => void;
}

const GlobalChatContext = createContext<GlobalChatContextType | undefined>(undefined);

interface GlobalChatProviderProps {
  children: ReactNode;
}

export function GlobalChatProvider({ children }: GlobalChatProviderProps) {
  // UI state
  const [isOpen, setIsOpen] = useState(false);
  const [selectedSucursal, setSelectedSucursal] = useState<any>(null);
  const [activeSessionId, setActiveSessionId] = useState<string>('global');
  const [sessionIds, setSessionIds] = useState<string[]>(['global']);

  // HUD terminal state
  const [chatWidth, setChatWidth] = useState(320); // Terminal width
  const [chatPosition, setChatPosition] = useState<'left' | 'right'>('right');
  const [showSidebar, setShowSidebar] = useState(false); // No sidebar

  // Use the existing orchestrator hook - ALWAYS use WebSocket
  const orchestrator = useOrchestratorChat(activeSessionId);
  const {
    messages,
    loading,
    summary,
    anomalies,
    dashboard,
    pendingActions,
    approvalReason,
    sendCommand,
    submitAction,
    hydrateMessages,
    appendLocalMessage,
    connection,
  } = orchestrator;
  const messageCacheRef = useRef<Record<string, OrchestratorMessage[]>>({});

  const {
    events: agentEvents,
    connect: connectAgentStream,
    disconnect: disconnectAgentStream,
  } = useAgentWebSocket();

  const processedAgentEventIdsRef = useRef<Set<string>>(new Set());

  const formatAgentEvent = useCallback((event: AgentEvent) => {
    const eventDate = event.timestamp ? new Date(event.timestamp) : new Date();
    const validDate = !Number.isNaN(eventDate.getTime());
    const displayDate = validDate ? eventDate : new Date();
    const formattedTime = displayDate.toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });

    const typeLabel = (event.type || 'evento')
      .toString()
      .replace(/_/g, ' ')
      .toUpperCase();

    const dataObject = (event.data && typeof event.data === 'object')
      ? (event.data as Record<string, unknown>)
      : undefined;

    const agentLabel = event.agent
      || (typeof dataObject?.agent === 'string' ? String(dataObject.agent) : 'system');
    const sessionLabel = event.session_id
      || (typeof dataObject?.session_id === 'string' ? String(dataObject.session_id) : undefined);

    const transition = event.from || event.to
      ? `${event.from ?? 'origin'} -> ${event.to ?? 'target'}`
      : null;

    let detail: string | null = null;

    if (typeof event.data === 'string') {
      detail = event.data;
    } else if (dataObject) {
      const candidateFields = ['message', 'detail', 'description', 'summary', 'status', 'reason', 'step'];
      for (const field of candidateFields) {
        const value = dataObject[field];
        if (typeof value === 'string' && value.trim()) {
          detail = value.trim();
          break;
        }
      }

      if (!detail && dataObject.state && typeof dataObject.state === 'object') {
        const stateData = dataObject.state as Record<string, unknown>;
        const stateFields = ['current_node', 'status', 'node'];
        for (const field of stateFields) {
          const value = stateData[field];
          if (typeof value === 'string' && value.trim()) {
            detail = `${field}: ${value.trim()}`;
            break;
          }
        }
      }

      if (!detail) {
        const dataEntries = Object.entries(dataObject)
          .filter(([key, value]) => typeof value === 'string' && key !== 'agent')
          .map(([key, value]) => `${key}: ${String(value).trim()}`)
          .slice(0, 2);
        if (dataEntries.length > 0) {
          detail = dataEntries.join(' | ');
        }
      }
    }

    if (detail && detail.length > 160) {
      detail = detail.slice(0, 157) + '...';
    }

    const segments = [
      `[${formattedTime}]`,
      `[${typeLabel}]`,
      `agent: ${agentLabel}`,
    ];

    if (sessionLabel) {
      segments.push(`session: ${sessionLabel}`);
    }

    if (transition) {
      segments.push(transition);
    }

    return detail ? `${segments.join(' ')} - ${detail}` : segments.join(' ');
  }, []);

  const getAgentEventKey = useCallback((event: AgentEvent) => {
    if (typeof event.id === 'string' && event.id.trim().length > 0) {
      return event.id.trim();
    }

    const fallbackParts = [
      event.type ?? '',
      event.timestamp ?? '',
      event.agent ?? '',
      event.session_id ?? '',
    ].filter(Boolean);

    if (fallbackParts.length > 0) {
      return fallbackParts.join('|');
    }

    try {
      return JSON.stringify(event).slice(0, 120);
    } catch {
      return `event-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    }
  }, []);

  useEffect(() => {
    connectAgentStream();
    return () => {
      disconnectAgentStream();
    };
  }, [connectAgentStream, disconnectAgentStream]);

  useEffect(() => {
    if (!Array.isArray(agentEvents) || agentEvents.length === 0) {
      return;
    }

    const seen = processedAgentEventIdsRef.current;
    const orderedEvents = [...agentEvents].reverse();
    const newMessages: OrchestratorMessage[] = [];

    for (const event of orderedEvents) {
      const key = getAgentEventKey(event);
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);

      const summary = formatAgentEvent(event);

      let eventAgent: string | undefined;
      if (typeof event.agent === 'string' && event.agent.trim()) {
        eventAgent = event.agent.trim();
      } else if (event.data && typeof event.data === 'object') {
        const agentValue = (event.data as Record<string, unknown>).agent;
        if (typeof agentValue === 'string' && agentValue.trim()) {
          eventAgent = agentValue.trim();
        }
      }

      newMessages.push({
        id: `agent-event-${key}`,
        role: 'system',
        content: summary,
        agent: eventAgent,
        payload: {
          type: 'agent_event',
          event,
        },
      });
    }

    if (newMessages.length > 0) {
      newMessages.forEach((message) => appendLocalMessage(message));
    }
  }, [agentEvents, formatAgentEvent, getAgentEventKey, appendLocalMessage]);

  const sanitizeSessionId = useCallback((sessionId: string) => {
    const cleaned = sessionId.replace(/[^A-Za-z0-9._-]/g, '_').slice(0, 128);
    return cleaned || 'default';
  }, []);

  const loadPersistedSession = useCallback(
    async (sessionId: string): Promise<OrchestratorMessage[]> => {
      const sanitized = sanitizeSessionId(sessionId);
      const manifestPath = `sessions/session_${sanitized}/session_${sanitized}.json`;
      try {
        const response = await fetch(
          `${API_BASE}/api/session-files/file?path=${encodeURIComponent(manifestPath)}`,
        );
        if (!response.ok) {
          throw new Error(`Status ${response.status}`);
        }
        const payload = await response.json();
        const history = Array.isArray(payload?.conversation_history)
          ? payload.conversation_history
          : [];
        let normalized = history
          .map((entry: any, index: number) => {
            const rawRole = typeof entry?.role === 'string' ? entry.role.toLowerCase() : 'system';
            const role: OrchestratorMessage['role'] = rawRole === 'assistant' || rawRole === 'ai'
              ? 'agent'
              : rawRole === 'system'
                ? 'system'
                : 'user';
            const content =
              typeof entry?.content === 'string'
                ? entry.content
                : typeof entry?.message === 'string'
                  ? entry.message
                  : '';
            if (!content) {
              return null;
            }
            return {
              id: `persisted-${sanitized}-${index}`,
              role,
              content,
              agent: typeof entry?.agent === 'string' ? entry.agent : undefined,
              payload: entry?.payload ?? entry?.data ?? undefined,
            } satisfies OrchestratorMessage;
          })
          .filter(Boolean) as OrchestratorMessage[];

        if (normalized.length === 0) {
          const fallback: OrchestratorMessage[] = [];
          const lastQuery = typeof payload?.last_query === 'string' ? payload.last_query.trim() : '';
          if (lastQuery) {
            fallback.push({
              id: `persisted-${sanitized}-user`,
              role: 'user',
              content: lastQuery,
            });
          }

          const lastResponse = payload?.last_response;
          const responseMessage = typeof lastResponse?.message === 'string' ? lastResponse.message.trim() : '';
          const summaryMessage = typeof payload?.response_message === 'string' ? payload.response_message.trim() : '';
          const metadataSummary = typeof payload?.response_metadata?.result_summary === 'string'
            ? payload.response_metadata.result_summary.trim()
            : '';
          const agentContent = responseMessage || summaryMessage || metadataSummary;

          if (agentContent) {
            const agentName = typeof lastResponse?.agent === 'string'
              ? lastResponse.agent
              : (typeof payload?.response_metadata?.agent === 'string' ? payload.response_metadata.agent : 'orquestador');
            fallback.push({
              id: `persisted-${sanitized}-agent`,
              role: 'agent',
              agent: agentName,
              content: agentContent,
              payload: lastResponse ?? payload?.response_metadata ?? undefined,
            });
          }

          normalized = fallback;
        }

        messageCacheRef.current[sessionId] = normalized;
        return normalized;
      } catch (error) {
        console.error(`No se pudo cargar el historial para la sesión ${sessionId}`, error);
        messageCacheRef.current[sessionId] = [];
        return [];
      }
    },
    [sanitizeSessionId],
  );

  useEffect(() => {
    let cancelled = false;
    const ensureHistory = async () => {
      const cached = messageCacheRef.current[activeSessionId];
      const snapshot = cached ? [...cached] : await loadPersistedSession(activeSessionId);
      if (!cancelled) {
        hydrateMessages(snapshot);
      }
    };
    void ensureHistory();
    return () => {
      cancelled = true;
    };
  }, [activeSessionId, hydrateMessages, loadPersistedSession]);

  useEffect(() => {
    messageCacheRef.current[activeSessionId] = messages;
  }, [activeSessionId, messages]);

  const refreshSessions = useCallback(async () => {
    try {
      const response = await fetch(`${API_BASE}/api/session-files/tree`);
      if (!response.ok) {
        throw new Error(`Error ${response.status} al obtener sesiones`);
      }
      const payload = await response.json();
      const entries: Array<Record<string, any>> = Array.isArray(payload?.entries) ? payload.entries : [];
      const sessionsEntry = entries.find((entry) => entry?.name === 'sessions');
      const discoveredIds: string[] = Array.isArray(sessionsEntry?.children)
        ? sessionsEntry.children
            .filter((child: any) => child?.type === 'directory')
            .map((child: any) => String(child?.name ?? ''))
            .filter(Boolean)
            .map((dirName: string) => dirName.replace(/^session_/, ''))
        : [];

      setSessionIds((prev) => {
        const next = new Set<string>(['global', ...prev, activeSessionId, ...discoveredIds]);
        return Array.from(next);
      });
    } catch (error) {
      console.error('No se pudieron refrescar las sesiones disponibles', error);
    }
  }, [activeSessionId]);

  useEffect(() => {
    void refreshSessions();
  }, [refreshSessions]);

  const createNewSession = useCallback(async () => {
    const timestamp = new Date().toISOString().replace(/[^0-9]/g, '').slice(0, 14);
    const newSessionId = `global-${timestamp}`;
    messageCacheRef.current[newSessionId] = [];
    setSessionIds((prev) => [newSessionId, ...prev.filter((id) => id !== newSessionId)]);
    setActiveSessionId(newSessionId);
    hydrateMessages([]);
    void refreshSessions();
    return newSessionId;
  }, [hydrateMessages, refreshSessions]);

  const switchSession = useCallback((sessionId: string) => {
    if (!sessionId) return;
    setSessionIds((prev) => [sessionId, ...prev.filter((id) => id !== sessionId)]);
    setActiveSessionId(sessionId);
  }, []);


  const contextValue: GlobalChatContextType = {
    // UI state
    isOpen,
    setIsOpen,

    // Pass through all orchestrator functionality
    messages,
    loading,
    summary,
    anomalies,
    dashboard,
    pendingActions,
    approvalReason,
    sendCommand,
    submitAction,
    connection,
    appendLocalMessage,

    activeSessionId,
    sessionIds,
    createNewSession,
    switchSession,
    refreshSessions,

    // Sucursal state
    selectedSucursal,
    setSelectedSucursal,

    // Layout customization
    chatWidth,
    setChatWidth,
    chatPosition,
    setChatPosition,
    showSidebar,
    setShowSidebar,
  };

  return (
    <GlobalChatContext.Provider value={contextValue}>
      {children}
    </GlobalChatContext.Provider>
  );
}

export function useGlobalChat() {
  const context = useContext(GlobalChatContext);
  if (context === undefined) {
    throw new Error('useGlobalChat must be used within a GlobalChatProvider');
  }
  return context;
}
