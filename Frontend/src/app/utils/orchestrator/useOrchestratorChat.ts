// Hook React para interactuar con el Orchestrator vía WebSocket únicamente.
// Enhanced with comprehensive logging for debugging WebSocket connections.
// Principios: logging detallado, error tracking, diagnósticos robustos.

import { useCallback, useEffect, useRef, useState } from 'react';
import { command, OrchestratorResult, submitHumanDecisionRequest } from './client';
import { OrchestratorSocket } from './ws';

// Create logger for hook-specific logging
class HookLogger {
  private static instance: HookLogger;
  
  static getInstance(): HookLogger {
    if (!HookLogger.instance) {
      HookLogger.instance = new HookLogger();
    }
    return HookLogger.instance;
  }

  private log(level: string, message: string, data?: any) {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] [HOOK-${level}] ${message}`;
    
    switch(level) {
      case 'INFO':
        console.log(logMsg, data || '');
        break;
      case 'WARN':
        console.warn(logMsg, data || '');
        break;
      case 'ERROR':
        console.error(logMsg, data || '');
        break;
      case 'DEBUG':
        console.debug(logMsg, data || '');
        break;
    }
  }

  info(message: string, data?: any) { this.log('INFO', message, data); }
  warn(message: string, data?: any) { this.log('WARN', message, data); }
  error(message: string, data?: any) { this.log('ERROR', message, data); }
  debug(message: string, data?: any) { this.log('DEBUG', message, data); }
}

const hookLogger = HookLogger.getInstance();

// Tipo interno de mensaje
export interface OrchestratorMessage {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  agent?: string;
  payload?: any;
}

export interface PendingAction {
  id: string;
  label: string;
  payload?: any;
  interrupt_id?: string | null;
  raw?: any;
}

export interface SubmitActionParams {
  actionId: string;
  approved: boolean;
  message?: string;
  reason?: string;
  metadata?: Record<string, any>;
}

interface HookReturn {
  messages: OrchestratorMessage[];
  loading: boolean;
  summary?: any;
  anomalies?: any[];
  dashboard?: any;
  pendingActions: PendingAction[];
  approvalReason: string | null;
  sendCommand: (text: string) => Promise<void>;
  submitAction: (params: SubmitActionParams) => Promise<void>;
  hydrateMessages: (history: OrchestratorMessage[]) => void;
  appendLocalMessage: (message: OrchestratorMessage) => void;
  connection: { status: 'idle' | 'connecting' | 'open' | 'reconnecting' | 'failed' | 'closed' };
}

let socketSingleton: OrchestratorSocket | null = null; // Lazy singleton

function ensureSocket(): OrchestratorSocket {
  if (!socketSingleton) {
    socketSingleton = new OrchestratorSocket();
    socketSingleton.connect();
  }
  return socketSingleton;
}

const STREAM_EVENT_TYPES = new Set([
  'node_transition',
  'agent_start',
  'agent_end',
  'agent_progress',
  'history',
  'state',
  'connection',
  'pong',
]);

function normalizeWSPayload(raw: any): OrchestratorMessage | null {
  if (!raw) return null;
  // Esperado: { agent, response } o { error }
  if (raw.error) {
    return {
      id: genId(),
      role: 'system',
      content: `Error: ${raw.error.message || raw.error.code}`,
      payload: raw,
    };
  }
  if (raw.agent && raw.response) {
    let printable: string;
    if (typeof raw.response === 'object' && raw.response) {
      // Preferir campos semánticos comunes
      const prefer = (raw.response.respuesta || raw.response.message || raw.response.mensaje);
      if (typeof prefer === 'string') {
        printable = prefer;
      } else {
        printable = JSON.stringify(raw.response).slice(0, 800);
      }
    } else {
      printable = String(raw.response);
    }
    return {
      id: genId(),
      role: 'agent',
      agent: raw.agent,
      content: printable,
      payload: raw.response,
    };
  }
  // Mensaje suelto o evento
  if (typeof raw === 'object' && typeof raw.type === 'string') {
    const type = raw.type.toLowerCase();
    if (STREAM_EVENT_TYPES.has(type)) {
      return null;
    }
    return {
      id: genId(),
      role: 'system',
      content: JSON.stringify(raw).slice(0, 400),
      payload: raw,
    };
  }
  if (typeof raw === 'string') {
    return { id: genId(), role: 'system', content: raw };
  }
  return null;
}

function genId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function normalizeActions(value: any): PendingAction[] {
  if (!value) return [];
  const items = Array.isArray(value) ? value : [value];
  const normalized: PendingAction[] = [];
  for (const raw of items) {
    if (!raw || typeof raw !== 'object') continue;
    const idRaw = (raw as any).id ?? (raw as any).action_id ?? (raw as any).key;
    if (!idRaw) continue;
    const labelRaw = (raw as any).label ?? (raw as any).title ?? (raw as any).description ?? 'Acción pendiente';
    normalized.push({
      id: String(idRaw),
      label: String(labelRaw),
      payload: (raw as any).payload ?? (raw as any).data ?? undefined,
      interrupt_id: (raw as any).interrupt_id ?? (raw as any).interruptId ?? null,
      raw,
    });
  }
  return normalized;
}

export function useOrchestratorChat(clientId: string = 'default'): HookReturn {
  const [messages, setMessages] = useState<OrchestratorMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [summary, setSummary] = useState<any>();
  const [anomalies, setAnomalies] = useState<any[]>();
  const [dashboard, setDashboard] = useState<any>();
  const [connStatus, setConnStatus] = useState<HookReturn['connection']['status']>('idle');
  const [pendingActions, setPendingActions] = useState<PendingAction[]>([]);
  const [approvalReason, setApprovalReason] = useState<string | null>(null);

  const socketRef = useRef<OrchestratorSocket | null>(null);
  
  // Log hook initialization
  useEffect(() => {
    hookLogger.info('useOrchestratorChat Hook Initialized', {
      clientId,
      messagesCount: messages.length,
      connStatus
    });
  }, [clientId, connStatus, messages.length]);

  useEffect(() => {
    setMessages([]);
    setSummary(undefined);
    setAnomalies(undefined);
    setDashboard(undefined);
  }, [clientId]);

  const applyResultSideData = useCallback((result: OrchestratorResult | null, rawPayload?: any) => {
    const candidateStrings: (string | undefined)[] = [];
    if (typeof rawPayload === 'string') {
      candidateStrings.push(rawPayload);
    } else if (rawPayload && typeof rawPayload === 'object') {
      const responseField = (rawPayload as any)?.response;
      if (typeof responseField === 'string') {
        candidateStrings.push(responseField);
      } else if (responseField && typeof responseField === 'object') {
        candidateStrings.push(responseField.respuesta, responseField.message, responseField.mensaje);
      }
      candidateStrings.push(
        (rawPayload as any)?.respuesta,
        (rawPayload as any)?.message,
        (rawPayload as any)?.mensaje,
      );
    }
    const friendlySummary =
      candidateStrings.find((value): value is string => typeof value === 'string' && value.trim().length > 0)?.trim() ?? null;

    if (friendlySummary) {
      setSummary(friendlySummary);
    } else if (result?.summary) {
      setSummary(result.summary);
    }

    if (result?.anomalies) setAnomalies(result.anomalies);
    if (result?.dashboard) setDashboard(result.dashboard);

    const metaCandidates = [
      rawPayload && typeof rawPayload === 'object' ? rawPayload.meta : undefined,
      rawPayload && typeof rawPayload === 'object' ? rawPayload.response_metadata : undefined,
      rawPayload && typeof rawPayload === 'object' ? rawPayload.metadata : undefined,
      (result as any)?.meta,
      (result as any)?.response_metadata,
    ].filter((candidate): candidate is Record<string, any> => !!candidate && typeof candidate === 'object');

    const metadata = metaCandidates.length > 0 ? metaCandidates[0] : undefined;

    if (metadata) {
      if (!friendlySummary && !result?.summary && metadata.result_summary) setSummary(metadata.result_summary);
      if (!result?.anomalies && metadata.anomalies) setAnomalies(metadata.anomalies);
      if (!result?.dashboard && metadata.dashboard) setDashboard(metadata.dashboard);
    }

    const normalizedActions = normalizeActions(
      rawPayload?.actions ??
      metadata?.actions ??
      (result as any)?.actions ??
      [],
    );

    const pendingFlag = Boolean(
      metadata?.el_cajas_pending ??
      metadata?.requires_human_approval ??
      rawPayload?.el_cajas_pending ??
      (normalizedActions.length > 0),
    );

    if (normalizedActions.length > 0) {
      setPendingActions(normalizedActions);
    } else if (!pendingFlag) {
      setPendingActions([]);
    }

    const derivedReason =
      metadata?.approval_reason ??
      rawPayload?.approval_reason ??
      (result as any)?.approval_reason ??
      null;

    if (pendingFlag) {
      setApprovalReason(derivedReason ?? null);
    } else {
      setApprovalReason(null);
    }
  }, []);

  // Inicializar socket y listeners
  useEffect(() => {
    const sock = ensureSocket();
    socketRef.current = sock;
    setConnStatus('connecting');

    const onOpen = () => setConnStatus('open');
    const onMessage = (payload: any) => {
      const msg = normalizeWSPayload(payload);
      if (msg) {
        setMessages(prev => {
          const updated = prev.map(m => {
            if (m.payload?.is_progress && !m.payload?.completed) {
              let nextContent = m.content;
              if (!nextContent.includes('?')) {
                const replaced = nextContent.replace('??', '?');
                nextContent = replaced !== nextContent ? replaced : `? ${nextContent}`;
              }
              return {
                ...m,
                content: nextContent,
                payload: { ...m.payload, completed: true },
              };
            }
            return m;
          });
          return [...updated, msg];
        });
        setLoading(false);

        if (msg.payload) {
          applyResultSideData(null, msg.payload);
        }
      }
    };
    const onError = () => setConnStatus(s => (s === 'open' ? 'open' : 'failed'));
    const onReconnecting = () => setConnStatus('reconnecting');
    const onClose = () => setConnStatus('closed');

    sock.on('open', onOpen);
    sock.on('message', onMessage);
    sock.on('error', onError);
    sock.on('reconnecting', onReconnecting);
    sock.on('close', onClose);
    sock.on('reconnect_failed', () => setConnStatus('failed'));

    // cleanup no cierra socket global para permitir reutilización en la app
    return () => {
      sock.off('open', onOpen);
      sock.off('message', onMessage);
      sock.off('error', onError);
      sock.off('reconnecting', onReconnecting);
      sock.off('close', onClose);
      sock.off('reconnect_failed', () => setConnStatus('failed'));
    };
  }, [applyResultSideData]);

  const appendUserMessage = useCallback((text: string) => {
    setMessages(prev => [...prev, { id: genId(), role: 'user', content: text }]);
  }, []);

  const finalizeAndAppend = useCallback((message: OrchestratorMessage) => {
  setMessages(prev => {
    const uplifted = prev.map(m => {
      if (m.payload?.is_progress && !m.payload?.completed) {
        let nextContent = m.content;
        if (!nextContent.includes('?')) {
          const replaced = nextContent.replace('??', '?');
          nextContent = replaced !== nextContent ? replaced : `? ${nextContent}`;
        }
        return {
          ...m,
          content: nextContent,
          payload: { ...m.payload, completed: true },
        };
      }
      return m;
    });
    return [...uplifted, message];
  });
  setLoading(false);
}, [setMessages]);

  const deliverAgentResponse = useCallback(
    (
      result: OrchestratorResult,
      rawPayload?: any,
      options?: { forceAppend?: boolean }
    ) => {
      const payloadForMeta =
        rawPayload ?? (result && typeof result === 'object' ? (result as any).response : undefined);

      applyResultSideData(result, payloadForMeta);

      const shouldAppend = options?.forceAppend ?? true;

      if (!shouldAppend) {
        return;
      }

      const agentName = result.agent || 'orchestrator';
      const responsePayload = result.response ?? result.data ?? result;

      let printable = '';

      if (typeof responsePayload === 'string') {
        printable = responsePayload;
      } else if (typeof result.message === 'string' && result.message.trim()) {
        printable = result.message;
      } else if (responsePayload && typeof responsePayload === 'object') {
        const semantic =
          (responsePayload as any)?.respuesta ||
          (responsePayload as any)?.message ||
          (responsePayload as any)?.mensaje;
        printable =
          typeof semantic === 'string' && semantic.trim()
            ? semantic
            : JSON.stringify(responsePayload).slice(0, 800);
      } else {
        printable = JSON.stringify(responsePayload ?? '').slice(0, 800);
      }

      finalizeAndAppend({
        id: genId(),
        role: 'agent',
        agent: agentName,
        content: printable,
        payload: responsePayload,
      });
    },
    [applyResultSideData, finalizeAndAppend],
  );

  const sendCommand = useCallback(async (text: string) => {
    if (!text.trim()) {
      hookLogger.warn('sendCommand called with empty text');
      return;
    }

    const commandId = Math.random().toString(36).slice(2, 8);
    hookLogger.info(`sendCommand Started [${commandId}]`, {
      textLength: text.length,
      textPreview: text.slice(0, 100),
      clientId,
      connStatus,
      messagesCount: messages.length
    });
    hookLogger.info(`[EMAIL_TRACE] frontend.dispatch`, {
      stage: 'before_send',
      commandId,
      rawInstruction: text
    });

    setPendingActions([]);
    setApprovalReason(null);
    appendUserMessage(text);
    setLoading(true);

    const sock = socketRef.current;
    const payload = { instruction: text, client_id: clientId };

    const handleHttpFallback = async (reason: string) => {
      hookLogger.warn(`Falling back to HTTP command [${commandId}]`, { reason });
      try {
        const result = await command(text, clientId);
        hookLogger.info(`HTTP Command Success [${commandId}]`, {
          hasAgent: !!result?.agent,
          hasResponse: !!result?.response,
        });
        deliverAgentResponse(result || {}, undefined, { forceAppend: true });
      } catch (httpError: any) {
        hookLogger.error(`HTTP Command Failed [${commandId}]`, {
          errorMessage: httpError?.message,
          errorCode: httpError?.code,
        });
        finalizeAndAppend({
          id: genId(),
          role: 'agent',
          agent: 'system',
          content: 'Error: No se pudo completar la consulta. Intenta nuevamente en unos segundos.',
          payload: { error: httpError?.message || httpError?.code || 'http_fallback_failed' },
        });
      }
    };

    const sendViaWebSocket = (socketWrapper: OrchestratorSocket | null): boolean => {
      if (!socketWrapper || !(socketWrapper as any)['ws']) {
        return false;
      }
      const wsInstance = (socketWrapper as any)['ws'] as WebSocket | undefined;
      if (!wsInstance) return false;

      if (wsInstance.readyState === WebSocket.OPEN) {
        try {
          const sent = socketWrapper.send(payload);
          hookLogger.info(`WebSocket Send Result [${commandId}]`, { sent });
          if (sent) {
            hookLogger.info(`WebSocket Command Sent Successfully [${commandId}] - awaiting response`);
            return true;
          }
        } catch (wsError: any) {
          hookLogger.error(`WebSocket Send Error [${commandId}]`, {
            error: wsError?.message,
            readyState: wsInstance.readyState,
          });
        }
        return false;
      }

      if (wsInstance.readyState === WebSocket.CONNECTING) {
        hookLogger.info(`WebSocket still connecting [${commandId}] - queuing send`);
        const onOpen = () => {
          socketWrapper.off('open', onOpen);
          const sentAfterOpen = sendViaWebSocket(socketWrapper);
          if (!sentAfterOpen) {
            hookLogger.warn(`Queued WebSocket send failed after open [${commandId}]`);
            void handleHttpFallback('ws-open-send-failed');
          }
        };
        socketWrapper.on('open', onOpen);
        return true;
      }

      return false;
    };

    hookLogger.info(`Attempting WebSocket Send [${commandId}]`, {
      sockExists: !!sock,
      wsExists: !!(sock as any)?.['ws'],
      wsReadyState: (sock as any)?.['ws']?.readyState,
      wsReadyStateOpen: WebSocket.OPEN
    });

    const wsSentOrQueued = sendViaWebSocket(sock);
    if (wsSentOrQueued) {
      return;
    }

    hookLogger.warn(`WebSocket unavailable, using HTTP fallback [${commandId}]`, {
      sockExists: !!sock,
      wsReadyState: (sock as any)?.['ws']?.readyState,
    });

    await handleHttpFallback('ws-not-available');
  }, [appendUserMessage, clientId, messages.length]);

  const submitAction = useCallback(async ({ actionId, approved, message, reason, metadata }: SubmitActionParams) => {
    const actionsSnapshot = pendingActions;
    if (!actionsSnapshot.length) {
      hookLogger.warn('submitAction invoked without pending actions', { actionId, approved });
      return;
    }

    const target = actionsSnapshot.find((action) => action.id === actionId) ?? actionsSnapshot[0];
    const resolvedId = target?.id ?? actionId;

    const metadataPayload: Record<string, any> = {
      action_id: resolvedId,
      label: target?.label,
      ...(target?.payload ? { action_payload: target.payload } : {}),
      ...(target?.raw ? { raw_action: target.raw } : {}),
      ...(metadata ?? {}),
    };

    setLoading(true);
    const requestId = Math.random().toString(36).slice(2, 8);
    hookLogger.info('submitAction dispatched', { requestId, actionId: resolvedId, approved, clientId });

    try {
      const response = await submitHumanDecisionRequest({
        session_id: clientId,
        approved,
        interrupt_id: target?.interrupt_id ?? undefined,
        message,
        reason,
        metadata: metadataPayload,
      });

      const envelope = response?.response;
      if (envelope && typeof envelope === 'object') {
        const agentName = envelope?.meta?.agent ?? envelope?.meta?.active_agent ?? envelope?.meta?.current_node ?? 'orquestador';
        const normalizedResult: OrchestratorResult = {
          agent: agentName,
          response: {
            respuesta: envelope?.message ?? '',
            message: envelope?.message ?? '',
            meta: envelope?.meta,
            data: envelope?.data,
            response_metadata: envelope?.meta,
          },
          summary: envelope?.meta?.result_summary,
          anomalies: envelope?.data?.anomalies,
          dashboard: envelope?.data?.dashboard,
        } as OrchestratorResult;
        deliverAgentResponse(normalizedResult, envelope, { forceAppend: true });
      } else {
        applyResultSideData(null, response);
        const fallbackMessage = response?.message ?? (approved ? 'Decisión registrada.' : 'Se registró la decisión.');
        finalizeAndAppend({
          id: genId(),
          role: 'agent',
          agent: 'orquestador',
          content: fallbackMessage,
          payload: response,
        });
      }
    } catch (error: any) {
      const errorMessage = error?.message || error?.code || 'No se pudo registrar la decisión humana.';
      hookLogger.error('submitAction failed', { requestId, actionId: resolvedId, errorMessage });
      finalizeAndAppend({
        id: genId(),
        role: 'agent',
        agent: 'system',
        content: `Error: ${errorMessage}`,
        payload: { source: 'human_decision', error: errorMessage, actionId: resolvedId },
      });
    } finally {
      setLoading(false);
    }
  }, [pendingActions, clientId, deliverAgentResponse, applyResultSideData, finalizeAndAppend]);

  const hydrateMessages = useCallback((history: OrchestratorMessage[]) => {
    setMessages(history);
  }, []);

  const appendLocalMessage = useCallback((message: OrchestratorMessage) => {
    setMessages((prev) => [...prev, message]);
  }, [setMessages]);

  return {
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
    connection: { status: connStatus },
  };
}

export default useOrchestratorChat;



