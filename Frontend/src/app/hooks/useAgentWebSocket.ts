/*
CAPI - Agent WebSocket Custom Hook
=================================
Ruta: /Frontend/src/app/hooks/useAgentWebSocket.ts
Descripción: Hook React personalizado para gestión de conexiones WebSocket con
agentes. Incluye reconexión automática, gestión de eventos y estado de conexión.
Estado: ✅ EN USO ACTIVO - PantallaAgentes core hook
Dependencias: React hooks, WebSocket API
Características: Reconexión automática, gestión eventos, estado conexión
Eventos: node_transition, agent_start, agent_end, ping/pong
Propósito: Comunicación en tiempo real con sistema de agentes
*/

'use client';

import { useEffect, useRef, useState, useCallback, useMemo } from 'react';
import { getApiBase } from '@/app/utils/orchestrator/client';

export interface AgentEvent {
  type: 'node_transition' | 'agent_start' | 'agent_end' | 'agent_progress' | 'connection' | 'history' | 'state' | 'pong' | 'error';
  id?: string;
  timestamp?: string;
  session_id?: string;
  from?: string;
  to?: string;
  agent?: string;
  ok?: boolean;
  duration_ms?: number;
  data?: any;
  meta?: Record<string, any>;
}

interface SessionStateSnapshot {
  sessionId: string;
  snapshot: any;
  updatedAt: string;
}

interface UseAgentWebSocketReturn {
  isConnected: boolean;
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'error';
  events: AgentEvent[];
  lastEvent: AgentEvent | null;
  lastTransition: AgentEvent | null;
  sessionStates: Record<string, SessionStateSnapshot>;
  activeSessionId: string | null;
  connect: () => void;
  disconnect: () => void;
  clearEvents: () => void;
  sendPing: () => void;
}

function buildAgentWebSocketUrl(explicitUrl?: string): string {
  const trimmed = explicitUrl?.trim();
  if (trimmed) {
    return trimmed;
  }

  try {
    const apiBase = getApiBase();
    const parsed = new URL(apiBase);
    parsed.protocol = parsed.protocol === 'https:' ? 'wss:' : 'ws:';
    parsed.pathname = '/ws/agents';
    parsed.search = '';
    parsed.hash = '';
    return parsed.toString();
  } catch (error) {
    console.warn('Falling back to default agent WebSocket URL', error);
    return 'ws://localhost:8000/ws/agents';
  }
}

const MAX_EVENTS = 100;
const RECONNECT_ATTEMPTS = 3;
const RECONNECT_DELAY = 2000;

export function useAgentWebSocket(rawUrl?: string): UseAgentWebSocketReturn {
  const wsUrl = useMemo(() => buildAgentWebSocketUrl(rawUrl), [rawUrl]);
  const [isConnected, setIsConnected] = useState(false);
  const [connectionState, setConnectionState] = useState<'connecting' | 'connected' | 'disconnected' | 'error'>('disconnected');
  const [events, setEvents] = useState<AgentEvent[]>([]);
  const [lastEvent, setLastEvent] = useState<AgentEvent | null>(null);

  const [sessionStates, setSessionStates] = useState<Record<string, SessionStateSnapshot>>({});
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [lastTransition, setLastTransition] = useState<AgentEvent | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttemptRef = useRef(0);
  const attemptReconnectRef = useRef<() => void>(() => {});
  const isManualDisconnectRef = useRef(false);

  const addEvent = useCallback((event: AgentEvent) => {
    setEvents(prev => {
      const newEvents = [event, ...prev].slice(0, MAX_EVENTS);
      return newEvents;
    });
    setLastEvent(event);
  }, []);

  const registerSessionSnapshot = useCallback((sessionId: string, snapshot: any, timestamp?: string) => {
    if (!sessionId) {
      return;
    }
    setSessionStates(prev => {
      const updated: Record<string, SessionStateSnapshot> = { ...prev };
      updated[sessionId] = {
        sessionId,
        snapshot,
        updatedAt: timestamp ?? new Date().toISOString()
      };
      const ordered = Object.values(updated)
        .sort((a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime())
        .slice(0, 10);
      return ordered.reduce<Record<string, SessionStateSnapshot>>((acc, entry) => {
        acc[entry.sessionId] = entry;
        return acc;
      }, {});
    });
  }, []);

  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data = JSON.parse(event.data);

      switch (data.type) {
        case 'node_transition': {
          const transition = data as AgentEvent;
          addEvent(transition);
          setLastTransition(transition);
          const sessionId = transition.session_id ?? transition.data?.session_id;
          if (sessionId) {
            setActiveSessionId(sessionId);
            if (transition.data?.state) {
              registerSessionSnapshot(sessionId, transition.data.state, transition.timestamp);
            }
          }
          break;
        }
        case 'agent_start':
        case 'agent_end':
        case 'agent_progress': {
          const agentEvent = data as AgentEvent;
          addEvent(agentEvent);
          if (agentEvent.session_id) {
            setActiveSessionId(agentEvent.session_id);
          }
          break;
        }
        case 'state': {
          const sessionId = data.session_id as string | undefined;
          if (sessionId && data.state) {
            registerSessionSnapshot(sessionId, data.state, data.timestamp);
            setActiveSessionId(prev => prev ?? sessionId);
          }
          break;
        }
        case 'history': {
          if (data.events && Array.isArray(data.events)) {
            setEvents(data.events.slice(0, MAX_EVENTS));
          }
          break;
        }
        case 'pong':
          console.debug('WebSocket pong received');
          break;
        case 'connection': {
          const connectionEvent = data as AgentEvent;
          addEvent(connectionEvent);
          if (connectionEvent.session_id) {
            setActiveSessionId(connectionEvent.session_id);
          }
          break;
        }
        default:
          addEvent(data as AgentEvent);
      }
    } catch (error) {
      console.error('Error parsing WebSocket message:', error);
    }
  }, [addEvent, registerSessionSnapshot, setEvents, setActiveSessionId, setLastTransition]);


  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN || wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    isManualDisconnectRef.current = false;
    setConnectionState('connecting');

    try {
      wsRef.current = new WebSocket(wsUrl);

      wsRef.current.onopen = () => {
        console.log('Agent WebSocket connected');
        setIsConnected(true);
        setConnectionState('connected');
        reconnectAttemptRef.current = 0;

        // Request recent event history
        wsRef.current?.send(JSON.stringify({
          type: 'get_history',
          limit: 20
        }));
      };

      wsRef.current.onmessage = handleMessage;

      wsRef.current.onerror = (error) => {
        console.error('Agent WebSocket error:', error);
        setConnectionState('error');
      };

      wsRef.current.onclose = () => {
        console.log('Agent WebSocket disconnected');
        setIsConnected(false);

        if (!isManualDisconnectRef.current) {
          setConnectionState('disconnected');
          attemptReconnectRef.current();
        } else {
          setConnectionState('disconnected');
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error);
      setConnectionState('error');
    }
  }, [wsUrl, handleMessage]);

  const attemptReconnect = useCallback(() => {
    if (isManualDisconnectRef.current || reconnectAttemptRef.current >= RECONNECT_ATTEMPTS) {
      setConnectionState('error');
      return;
    }

    reconnectAttemptRef.current += 1;
    reconnectTimeoutRef.current = setTimeout(() => {
      connect();
    }, RECONNECT_DELAY * reconnectAttemptRef.current);
  }, [connect]);

  useEffect(() => {
    attemptReconnectRef.current = attemptReconnect;
  }, [attemptReconnect]);

  const disconnect = useCallback(() => {
    isManualDisconnectRef.current = true;

    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setIsConnected(false);
    setConnectionState('disconnected');
    setActiveSessionId(null);
    setLastTransition(null);
  }, []);

  const clearEvents = useCallback(() => {
    setEvents([]);
    setLastEvent(null);
    setLastTransition(null);
  }, []);

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'ping',
        timestamp: new Date().toISOString()
      }));
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  return {
    isConnected,
    connectionState,
    events,
    lastEvent,
    lastTransition,
    sessionStates,
    activeSessionId,
    connect,
    disconnect,
    clearEvents,
    sendPing
  };
}

