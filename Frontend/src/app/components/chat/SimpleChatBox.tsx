import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import Image from 'next/image';
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';
import VoiceInterface from './voice/VoiceInterface';
import { Message, ChatBoxProps } from '@/app/types/chat';

// Design tokens - consistent with HUD system
const THEME = {
  colors: {
    primary: '#00e5ff',      // hud-accent
    primaryAlt: '#7df9ff',   // hud-accent-2
    success: '#12d48a',      // hud-ok
    text: '#e6f1ff',         // hud-text
    textMuted: '#8aa0c5',    // hud-muted
    bg: '#0a0f1c',           // hud-bg
    panel: 'rgba(14, 22, 38, 0.85)', // hud-panel
    border: '#1d2b4a'        // hud-border
  },
  spacing: { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24 },
  fonts: {
    heading: "'Orbitron', ui-sans-serif, system-ui, sans-serif",
    ui: "'Inter', ui-sans-serif, system-ui, sans-serif"
  }
} as const;

// Task status for agent progress
interface TaskStep {
  id: string;
  text: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  timestamp?: number;
}

interface ProcessingMessage {
  id: string;
  agent: string;
  tasks: TaskStep[];
  startTime: number;
}

export default function SimpleChatBox({ sucursal, onRemoveSucursal }: ChatBoxProps) {
  const [input, setInput] = useState('');
  const [alertContext, setAlertContext] = useState<{text: string, context: any} | null>(null);
  const [processingMessage, setProcessingMessage] = useState<ProcessingMessage | null>(null);

  // Use global chat context instead of local hook
  const {
    messages,
    loading,
    sendCommand,
    submitAction,
    pendingActions,
    approvalReason,
    connection,
    appendLocalMessage,
    activeSessionId
  } = useGlobalChat();

  const [actionSubmitting, setActionSubmitting] = useState(false);
  const currentPendingAction = useMemo(() => pendingActions[0] ?? null, [pendingActions]);
  const pendingActionDetails = useMemo(() => {
    if (!currentPendingAction) return null;
    const payload = currentPendingAction.payload ?? {};
    const fileCandidate = payload.artifact_filename ?? payload.filename ?? payload.relative_path ?? payload.path;
    const branchCandidate = payload.branch_name ?? payload.branch;
    const summaryCandidate = typeof payload.summary === 'string' && payload.summary.trim() ? payload.summary : null;
    const hypothesisCandidate = typeof payload.hypothesis === 'string' && payload.hypothesis.trim() ? payload.hypothesis : null;
    return {
      fileName: typeof fileCandidate === 'string' && fileCandidate.trim() ? fileCandidate : null,
      branchName: typeof branchCandidate === 'string' && branchCandidate.trim() ? branchCandidate : null,
      summary: summaryCandidate ?? hypothesisCandidate,
    };
  }, [currentPendingAction]);

  const isDecisionDisabled = actionSubmitting || loading;

  const transformedMessages: Message[] = useMemo(() => {
    const now = Date.now();
    return messages.map((m: any, index: number) => {
      const payload = (m && typeof m === 'object') ? m.payload ?? {} : {};
      const rawEvent = payload && typeof payload === 'object' ? (payload as any).event : undefined;

      const preferredText =
        typeof payload?.respuesta === 'string' && payload.respuesta.trim()
          ? payload.respuesta
          : typeof payload?.message === 'string' && payload.message.trim()
            ? payload.message
            : undefined;

      const fallbackContent = typeof m?.content === 'string' ? m.content : '';
      const fallbackEventText = rawEvent ? JSON.stringify(rawEvent).slice(0, 400) : '';

      const text = preferredText || fallbackContent || fallbackEventText || '';

      const messageKind =
        typeof payload?.type === 'string' && payload.type.trim()
          ? payload.type
          : rawEvent
            ? 'agent_event'
            : m?.role === 'system'
              ? 'system'
              : 'conversation';

      const candidateTimestamps: Array<string | number | undefined> = [
        payload?.timestamp,
        payload?.time,
        payload?.meta?.timestamp,
        rawEvent?.timestamp,
        rawEvent?.time,
      ];

      let timestamp: number | undefined;
      for (const candidate of candidateTimestamps) {
        if (typeof candidate === 'number' && !Number.isNaN(candidate)) {
          timestamp = candidate;
          break;
        }
        if (typeof candidate === 'string') {
          const parsed = Date.parse(candidate);
          if (!Number.isNaN(parsed)) {
            timestamp = parsed;
            break;
          }
        }
      }
      if (timestamp === undefined) {
        timestamp = now - (messages.length - index) * 1000;
      }

      let agentName: string | undefined;
      if (typeof m?.agent === 'string' && m.agent.trim()) {
        agentName = m.agent.trim();
      } else if (typeof payload?.agent === 'string' && payload.agent.trim()) {
        agentName = payload.agent.trim();
      } else if (rawEvent && typeof rawEvent.agent === 'string' && rawEvent.agent.trim()) {
        agentName = rawEvent.agent.trim();
      }

      return {
        id: typeof m?.id === 'string' ? m.id : `msg-${index}`,
        sender: m?.role === 'user' ? 'user' : m?.role === 'system' ? 'system' : 'bot',
        text,
        agent: agentName,
        timestamp,
        kind: messageKind,
        payload,
        raw: m,
      } as Message;
    });
  }, [messages]);

  // Simulate agent task processing when loading
  useEffect(() => {
    if (loading && !processingMessage) {
      const mockTasks: TaskStep[] = [
        { id: '1', text: 'Analyzing financial data', status: 'running' },
        { id: '2', text: 'Processing branch metrics', status: 'pending' },
        { id: '3', text: 'Generating insights', status: 'pending' },
        { id: '4', text: 'Compiling response', status: 'pending' }
      ];

      setProcessingMessage({
        id: `proc-${Date.now()}`,
        agent: 'CAPI',
        tasks: mockTasks,
        startTime: Date.now()
      });

      // Simulate task progression
      const simulateProgress = async () => {
        for (let i = 0; i < mockTasks.length; i++) {
          await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 600));

          setProcessingMessage(prev => {
            if (!prev) return prev;
            const newTasks = [...prev.tasks];
            if (i > 0) newTasks[i - 1].status = 'complete';
            newTasks[i].status = 'running';
            return { ...prev, tasks: newTasks };
          });
        }
      };

      simulateProgress();
    } else if (!loading && processingMessage) {
      // Mark all tasks complete
      setProcessingMessage(prev => {
        if (!prev) return prev;
        const completedTasks = prev.tasks.map(task => ({ ...task, status: 'complete' as const }));
        return { ...prev, tasks: completedTasks };
      });

      // Remove processing message after delay
      setTimeout(() => setProcessingMessage(null), 1000);
    }
  }, [loading, processingMessage]);

  // Expert-level alert-chat integration system
  useEffect(() => {
    const handleAlertContext = (event: any) => {
      if (event.detail?.text && event.detail?.context) {
        setAlertContext({
          text: event.detail.text,
          context: event.detail.context
        });
      }
    };

    window.addEventListener('add-to-chat', handleAlertContext);
    return () => window.removeEventListener('add-to-chat', handleAlertContext);
  }, []);

  // Accept alert context into input
  const acceptAlertContext = useCallback(() => {
    if (alertContext) {
      setInput(alertContext.text);
      setAlertContext(null);
    }
  }, [alertContext]);

  // Reject alert context
  const rejectAlertContext = useCallback(() => {
    setAlertContext(null);
  }, []);

  const handleActionDecision = useCallback(async (approved: boolean) => {
    if (!currentPendingAction) {
      return;
    }

    try {
      setActionSubmitting(true);
      await submitAction({ actionId: currentPendingAction.id, approved });
    } catch (error) {
      console.error('No se pudo registrar la decisión humana', error);
    } finally {
      setActionSubmitting(false);
    }
  }, [currentPendingAction, submitAction]);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const element = messagesEndRef.current;
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [transformedMessages.length]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const inputToSend = input;
    const contextInfo = alertContext?.context;
    setInput('');
    setAlertContext(null); // Clear context after sending

    try {
      await sendCommand(inputToSend);

      // If there was context, show it was used in the message
      if (contextInfo) {
        console.log('Message sent with alert context from:', contextInfo.agent);
      }
    } catch (error: any) {
      setInput(inputToSend);
      // Restore context if send failed
      if (contextInfo) {
        setAlertContext({ text: inputToSend, context: contextInfo });
      }
    }
  }, [input, loading, sendCommand, alertContext]);

  const handleVoiceMessageAppend = useCallback((message: { role: 'user' | 'agent' | 'system'; content: string; metadata?: Record<string, unknown>; agent?: string }) => {
    const trimmedContent = typeof message.content === 'string' ? message.content.trim() : '';
    if (!trimmedContent) {
      return;
    }

    const normalizedRole: 'user' | 'agent' | 'system' = message.role === 'agent' ? 'agent' : message.role === 'system' ? 'system' : 'user';
    const generatedId = `voice-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
    const payload = {
      modality: 'voice',
      ...(message.metadata ?? {}),
    };

    appendLocalMessage({
      id: generatedId,
      role: normalizedRole,
      content: trimmedContent,
      agent: message.agent ?? (normalizedRole === 'agent' ? 'voz' : undefined),
      payload,
    });
  }, [appendLocalMessage]);

  // Format timestamp for messages
  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Render task step component
  const renderTaskStep = (task: TaskStep, index: number) => {
    const getStatusConfig = () => {
      switch (task.status) {
        case 'complete':
          return {
            icon: '●',
            color: THEME.colors.success,
            bgColor: THEME.colors.success + '15',
            borderColor: THEME.colors.success + '30'
          };
        case 'running':
          return {
            icon: '●',
            color: THEME.colors.primary,
            bgColor: THEME.colors.primary + '15',
            borderColor: THEME.colors.primary + '40'
          };
        case 'error':
          return {
            icon: '●',
            color: '#ff6b6b',
            bgColor: '#ff6b6b15',
            borderColor: '#ff6b6b30'
          };
        default:
          return {
            icon: '○',
            color: THEME.colors.textMuted,
            bgColor: 'transparent',
            borderColor: THEME.colors.textMuted + '20'
          };
      }
    };

    const config = getStatusConfig();

    return (
      <div key={task.id} style={{
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        padding: '6px 8px',
        fontSize: '12px',
        background: config.bgColor,
        border: `1px solid ${config.borderColor}`,
        borderRadius: '6px',
        marginBottom: '4px'
      }}>
        <div style={{
          width: '6px',
          height: '6px',
          borderRadius: '50%',
          backgroundColor: config.color,
          flexShrink: 0,
          boxShadow: task.status === 'running' ? `0 0 6px ${config.color}` : 'none',
          animation: task.status === 'running' ? 'pulse 1s infinite' : 'none'
        }} />
        <span style={{
          fontFamily: THEME.fonts.ui,
          color: THEME.colors.text,
          flex: 1
        }}>
          {task.text}
        </span>
      </div>
    );
  };

  const renderAgentEventMessage = (msg: Message, index: number) => {
    const eventPayload =
      (msg.raw as any)?.payload?.event ??
      (msg.payload as any)?.event ??
      msg.payload;

    const detailLines: string[] = [];

    if (msg.timestamp) {
      detailLines.push(`hora ${formatTime(msg.timestamp)}`);
    }

    if (msg.agent) {
      detailLines.push(`agente ${msg.agent}`);
    }

    if (eventPayload && typeof eventPayload === 'object') {
      const eventObject = eventPayload as Record<string, any>;

      if (typeof eventObject.type === 'string' && eventObject.type.trim()) {
        detailLines.push(`evento ${eventObject.type}`);
      }

      const sessionCandidate =
        typeof eventObject.session_id === 'string' && eventObject.session_id.trim()
          ? eventObject.session_id
          : typeof eventObject.data?.session_id === 'string' && eventObject.data.session_id.trim()
            ? eventObject.data.session_id
            : undefined;

      if (sessionCandidate) {
        detailLines.push(`sesion ${sessionCandidate}`);
      }

      if (eventObject.from || eventObject.to) {
        detailLines.push(`flujo ${eventObject.from ?? 'origen'} -> ${eventObject.to ?? 'destino'}`);
      }

      if (typeof eventObject.duration_ms === 'number') {
        detailLines.push(`duracion ${Math.round(eventObject.duration_ms)} ms`);
      }

      const dataPreview =
        eventObject.data && typeof eventObject.data === 'object'
          ? (eventObject.data as Record<string, unknown>)
          : undefined;

      if (dataPreview) {
        const previewEntries = Object.entries(dataPreview)
          .filter(([key, value]) => (typeof value === 'string' || typeof value === 'number') && !['session_id', 'agent'].includes(key))
          .slice(0, 2);

        previewEntries.forEach(([key, value]) => {
          detailLines.push(`${key}: ${String(value)}`);
        });
      }
    }

    const uniqueLines = Array.from(new Set(detailLines)).slice(0, 5);

    return (
      <div
        key={msg.id ?? `agent-event-${index}`}
        style={{
          marginBottom: '12px',
          padding: '6px 0',
          borderBottom: `1px solid ${THEME.colors.border}`,
          fontFamily: THEME.fonts.ui,
        }}
      >
        <div
          style={{
            fontSize: '12px',
            color: THEME.colors.text,
            whiteSpace: 'pre-wrap',
            lineHeight: 1.5,
          }}
        >
          {msg.text}
        </div>
        {uniqueLines.length > 0 && (
          <div
            style={{
              marginTop: '4px',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
            }}
          >
            {uniqueLines.map((line, detailIndex) => (
              <span
                key={`${msg.id ?? index}-detail-${detailIndex}`}
                style={{
                  fontSize: '11px',
                  color: THEME.colors.textMuted,
                  whiteSpace: 'pre-wrap',
                }}
              >
                {line}
              </span>
            ))}
          </div>
        )}
      </div>
    );
  };

  // Render message with HUD-friendly design
  const renderMessage = (msg: Message, index: number) => {
    if (msg.kind === 'agent_event') {
      return renderAgentEventMessage(msg, index);
    }

    const isUser = msg.sender === 'user';
    const isSystem = msg.sender === 'system';
    const displayAgentName = msg.agent && msg.agent.trim().length > 0
      ? msg.agent
      : isSystem
        ? 'Sistema'
        : 'CAPI';
    const agentInitial = displayAgentName.slice(0, 1).toUpperCase();
    const timestampLabel = typeof msg.timestamp === 'number' ? formatTime(msg.timestamp) : '';

    return (
      <div key={msg.id ?? `msg-${index}`} style={{
        display: 'flex',
        flexDirection: 'column',
        marginBottom: '20px',
        gap: '8px'
      }}>
        {/* Message header with avatar and timestamp */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          justifyContent: isUser ? 'flex-end' : 'flex-start'
        }}>
          {!isUser && (
            <>
              <div style={{
                width: '20px',
                height: '20px',
                borderRadius: '4px',
                background: `linear-gradient(135deg, ${THEME.colors.primary}, ${THEME.colors.primaryAlt})`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '8px',
                fontFamily: THEME.fonts.heading,
                color: THEME.colors.bg,
                flexShrink: 0,
                boxShadow: `0 0 8px ${THEME.colors.primary}30`
              }}>
                {agentInitial}
              </div>
              <span style={{
                fontSize: '11px',
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.ui,
                letterSpacing: '0.05em'
              }}>
                {displayAgentName}
              </span>
            </>
          )}

          <div style={{
            fontSize: '10px',
            color: THEME.colors.textMuted + '80',
            fontFamily: THEME.fonts.ui,
            marginLeft: isUser ? '0' : 'auto',
            marginRight: isUser ? 'auto' : '0'
          }}>
            {timestampLabel}
          </div>

          {isUser && (
            <>
              <span style={{
                fontSize: '11px',
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.ui,
                letterSpacing: '0.05em'
              }}>
                You
              </span>
              <div style={{
                width: '20px',
                height: '20px',
                borderRadius: '4px',
                background: `linear-gradient(135deg, ${THEME.colors.textMuted}, ${THEME.colors.textMuted}80)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '8px',
                fontFamily: THEME.fonts.heading,
                color: THEME.colors.bg,
                flexShrink: 0
              }}>
                U
              </div>
            </>
          )}
        </div>

        {/* Message content */}
        <div style={{
          display: 'flex',
          justifyContent: isUser ? 'flex-end' : 'flex-start'
        }}>
          <div style={{
            maxWidth: '85%',
            padding: '14px 18px',
            background: isUser
              ? `linear-gradient(135deg, ${THEME.colors.primary}12, ${THEME.colors.primary}08)`
              : THEME.colors.panel,
            border: `1px solid ${isUser ? THEME.colors.primary + '25' : THEME.colors.border}`,
            borderRadius: '12px',
            color: THEME.colors.text,
            fontFamily: THEME.fonts.ui,
            fontSize: '13px',
            lineHeight: '1.5',
            boxShadow: isUser
              ? `0 2px 12px ${THEME.colors.primary}15`
              : '0 4px 16px rgba(0, 0, 0, 0.25)',
            position: 'relative'
          }}>
            {/* Subtle HUD accent corner */}
            <div style={{
              position: 'absolute',
              top: '6px',
              [isUser ? 'right' : 'left']: '6px',
              width: '6px',
              height: '6px',
              border: `1px solid ${isUser ? THEME.colors.primary + '40' : THEME.colors.border}`,
              borderRadius: '1px',
              [isUser ? 'borderLeft' : 'borderRight']: 'none',
              [isUser ? 'borderBottom' : 'borderBottom']: 'none'
            }} />

            {msg.text}
          </div>
        </div>
      </div>
    );
  };

  const handleInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: `
        linear-gradient(135deg,
          rgba(0, 12, 25, 0.98) 0%,
          rgba(0, 20, 40, 0.98) 50%,
          rgba(0, 8, 17, 0.98) 100%
        )
      `,
      borderRadius: '6px',
      border: '1px solid rgba(0, 255, 255, 0.4)',
      boxShadow: `
        0 0 30px rgba(0, 255, 255, 0.15),
        0 0 60px rgba(0, 200, 255, 0.08),
        0 0 100px rgba(0, 150, 255, 0.04),
        inset 0 1px 0 rgba(0, 255, 255, 0.3),
        inset 0 -1px 0 rgba(0, 255, 255, 0.1)
      `,
      overflow: 'hidden',
      fontFamily: THEME.fonts.ui,
      position: 'relative',
      backdropFilter: 'blur(8px)'
    }}>
      {/* Premium glass morphism overlay */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: `
          radial-gradient(circle at 20% 20%, rgba(0, 255, 255, 0.05) 0%, transparent 50%),
          radial-gradient(circle at 80% 80%, rgba(0, 200, 255, 0.03) 0%, transparent 50%)
        `,
        pointerEvents: 'none',
        zIndex: 0
      }} />
      {/* Premium HUD Header */}
      <div style={{
        padding: '14px 18px',
        background: `
          linear-gradient(135deg,
            rgba(0, 15, 30, 0.95) 0%,
            rgba(0, 25, 50, 0.9) 50%,
            rgba(0, 12, 25, 0.95) 100%
          )
        `,
        borderBottom: '1px solid rgba(0, 255, 255, 0.3)',
        borderRadius: '6px 6px 0 0',
        position: 'relative',
        zIndex: 2
      }}>
        {/* Premium top accent line */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: '15%',
          right: '15%',
          height: '1px',
          background: `
            linear-gradient(90deg,
              transparent 0%,
              rgba(0, 255, 255, 0.8) 20%,
              rgba(0, 200, 255, 0.9) 50%,
              rgba(0, 255, 255, 0.8) 80%,
              transparent 100%
            )
          `,
          boxShadow: '0 0 4px rgba(0, 255, 255, 0.5)'
        }} />

        {/* Corner accents */}
        <div style={{
          position: 'absolute',
          top: '2px',
          left: '2px',
          width: '12px',
          height: '12px',
          border: '1px solid rgba(0, 255, 255, 0.4)',
          borderRight: 'none',
          borderBottom: 'none',
          borderRadius: '2px 0 0 0'
        }} />
        <div style={{
          position: 'absolute',
          top: '2px',
          right: '2px',
          width: '12px',
          height: '12px',
          border: '1px solid rgba(0, 255, 255, 0.4)',
          borderLeft: 'none',
          borderBottom: 'none',
          borderRadius: '0 2px 0 0'
        }} />

        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'relative',
          zIndex: 1
        }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px'
          }}>
            {/* Premium status indicator */}
            <div style={{
              position: 'relative',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <div style={{
                width: '8px',
                height: '8px',
                backgroundColor: connection.status === 'open' ? '#00ffff' : '#ff6b6b',
                borderRadius: '50%',
                boxShadow: connection.status === 'open'
                  ? '0 0 12px #00ffff, 0 0 24px rgba(0, 255, 255, 0.3)'
                  : '0 0 12px #ff6b6b',
                animation: connection.status === 'open' ? 'pulse 2s infinite' : 'none',
                border: '1px solid rgba(255, 255, 255, 0.1)'
              }} />
              <div style={{
                position: 'absolute',
                left: '0',
                top: '0',
                width: '8px',
                height: '8px',
                borderRadius: '50%',
                background: connection.status === 'open' ? 'rgba(0, 255, 255, 0.2)' : 'rgba(255, 107, 107, 0.2)',
                animation: connection.status === 'open' ? 'ping 2s cubic-bezier(0, 0, 0.2, 1) infinite' : 'none'
              }} />
            </div>

            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '1px'
            }}>
              <span style={{
                color: THEME.colors.primaryAlt,
                fontSize: '11px',
                fontWeight: 700,
                letterSpacing: '0.15em',
                textTransform: 'uppercase',
                fontFamily: THEME.fonts.heading,
                textShadow: '0 0 8px rgba(0, 255, 255, 0.3)'
              }}>
                CAPI
              </span>
            </div>
          </div>

          {/* Expert Context Indicator */}
          {alertContext && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 8px',
              background: `linear-gradient(135deg, ${THEME.colors.primary}20, ${THEME.colors.primary}10)`,
              border: `1px solid ${THEME.colors.primary}40`,
              borderRadius: '4px',
              fontSize: '9px',
              color: THEME.colors.primary,
              fontFamily: THEME.fonts.ui,
              letterSpacing: '0.05em',
              textTransform: 'uppercase',
              boxShadow: `0 0 8px ${THEME.colors.primary}20`,
              animation: 'contextPulse 2s infinite'
            }}>
              <div style={{
                width: '4px',
                height: '4px',
                backgroundColor: THEME.colors.primary,
                borderRadius: '50%',
                boxShadow: `0 0 4px ${THEME.colors.primary}`,
                animation: 'pulse 1s infinite'
              }} />
              Context: {alertContext.context?.agent || 'Alert'}
            </div>
          )}

        </div>
      </div>
      <div style={{
        flex: 1,
        padding: '0',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        background: `
          radial-gradient(ellipse at center,
            rgba(0, 15, 30, 0.8) 0%,
            rgba(0, 8, 17, 0.95) 70%,
            rgba(0, 4, 10, 0.98) 100%
          )
        `,
        position: 'relative'
      }}>
        {/* Advanced holographic grid */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `
            linear-gradient(90deg, transparent 98%, rgba(0, 255, 255, 0.02) 100%),
            linear-gradient(0deg, transparent 98%, rgba(0, 255, 255, 0.015) 100%)
          `,
          backgroundSize: '25px 25px',
          pointerEvents: 'none',
          zIndex: 1,
          opacity: 0.6
        }} />

        {/* Flowing data streams */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: '10%',
          width: '1px',
          height: '100%',
          background: 'linear-gradient(to bottom, transparent, rgba(0, 255, 255, 0.2), transparent)',
          animation: 'dataFlow 8s linear infinite',
          pointerEvents: 'none',
          zIndex: 1
        }} />
        <div style={{
          position: 'absolute',
          top: 0,
          right: '15%',
          width: '1px',
          height: '100%',
          background: 'linear-gradient(to bottom, transparent, rgba(0, 200, 255, 0.15), transparent)',
          animation: 'dataFlow 12s linear infinite reverse',
          pointerEvents: 'none',
          zIndex: 1
        }} />

        {/* Premium content area */}
        <div style={{
          flex: 1,
          overflowY: 'scroll',
          padding: '20px 24px',
          paddingRight: '16px',
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(0, 255, 255, 0.4) transparent',
          position: 'relative',
          zIndex: 2
        }}>
        {sucursal && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '8px 12px',
            backgroundColor: 'rgba(0, 255, 136, 0.1)',
            borderRadius: '8px',
            border: '1px solid rgba(0, 255, 136, 0.2)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Image src="/clip.svg" alt="clip" width={16} height={16} />
              <span style={{ color: '#00ff88', fontSize: '14px', fontWeight: 500 }}>{sucursal.sucursal_nombre}</span>
            </div>
            <button
              onClick={onRemoveSucursal}
              aria-label="Eliminar sucursal"
              style={{
                background: 'rgba(255, 107, 107, 0.2)',
                border: '1px solid rgba(255, 107, 107, 0.3)',
                borderRadius: '4px',
                cursor: 'pointer',
                padding: '4px 8px',
                color: '#ff6b6b',
                fontSize: '12px',
                fontWeight: 500,
                transition: 'all 0.2s ease'
              }}
            >
              Quitar
            </button>
          </div>
        )}

        {transformedMessages.length === 0 && !processingMessage ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              backgroundColor: THEME.colors.primary,
              borderRadius: '50%',
              boxShadow: `0 0 16px ${THEME.colors.primary}`,
              animation: 'pulse 2s infinite'
            }} />
            <div style={{
              color: THEME.colors.textMuted,
              fontSize: '12px',
              fontFamily: THEME.fonts.ui,
              textAlign: 'center'
            }}>
              Ready to assist
            </div>
          </div>
        ) : (
          <>
            {transformedMessages.map(renderMessage)}

            {/* Processing message with task steps */}
            {processingMessage && (
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                marginBottom: '20px',
                gap: '8px'
              }}>
                {/* Processing header */}
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  justifyContent: 'flex-start'
                }}>
                  <div style={{
                    width: '20px',
                    height: '20px',
                    borderRadius: '4px',
                    background: `linear-gradient(135deg, ${THEME.colors.primary}, ${THEME.colors.primaryAlt})`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '8px',
                    fontFamily: THEME.fonts.heading,
                    color: THEME.colors.bg,
                    flexShrink: 0,
                    boxShadow: `0 0 12px ${THEME.colors.primary}40`,
                    animation: 'pulse 1.5s infinite'
                  }}>
                    C
                  </div>
                  <span style={{
                    fontSize: '11px',
                    color: THEME.colors.textMuted,
                    fontFamily: THEME.fonts.ui,
                    letterSpacing: '0.05em'
                  }}>
                    CAPI is thinking...
                  </span>
                  <div style={{
                    fontSize: '10px',
                    color: THEME.colors.textMuted + '80',
                    fontFamily: THEME.fonts.ui,
                    marginLeft: 'auto'
                  }}>
                    {formatTime(processingMessage.startTime)}
                  </div>
                </div>

                {/* Processing content */}
                <div style={{
                  display: 'flex',
                  justifyContent: 'flex-start'
                }}>
                  <div style={{
                    maxWidth: '85%',
                    padding: '16px 18px',
                    background: THEME.colors.panel,
                    border: `1px solid ${THEME.colors.border}`,
                    borderRadius: '12px',
                    boxShadow: '0 4px 16px rgba(0, 0, 0, 0.25)',
                    position: 'relative'
                  }}>
                    {/* HUD accent corner */}
                    <div style={{
                      position: 'absolute',
                      top: '6px',
                      left: '6px',
                      width: '6px',
                      height: '6px',
                      border: `1px solid ${THEME.colors.border}`,
                      borderRadius: '1px',
                      borderRight: 'none',
                      borderBottom: 'none'
                    }} />

                    <div style={{
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '8px'
                    }}>
                      {processingMessage.tasks.map(renderTaskStep)}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        <div ref={messagesEndRef} />
        </div>
      </div>

      {currentPendingAction && (
        <div
          style={{
            margin: '12px 20px 0',
            padding: '14px 16px',
            borderRadius: '8px',
            border: `1px solid ${THEME.colors.primary}40`,
            background: 'linear-gradient(135deg, rgba(0, 255, 255, 0.08), rgba(0, 255, 255, 0.03))',
            boxShadow: '0 6px 18px rgba(0, 0, 0, 0.35)',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div
              style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: THEME.colors.primary,
                boxShadow: `0 0 10px ${THEME.colors.primary}80`,
                animation: 'pulse 2s infinite'
              }}
            />
            <span
              style={{
                fontSize: '11px',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
                fontFamily: THEME.fonts.heading,
                color: THEME.colors.primaryAlt
              }}
            >
              Acción requerida
            </span>
            <span
              style={{
                marginLeft: 'auto',
                fontSize: '10px',
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.ui
              }}
            >
              {currentPendingAction.label}
            </span>
          </div>

          <div
            style={{
              fontSize: '11px',
              color: THEME.colors.text,
              fontFamily: THEME.fonts.ui,
              lineHeight: '1.4'
            }}
          >
            {approvalReason || '¿Deseas ejecutar la acción sugerida?'}
          </div>

          {pendingActionDetails?.fileName && (
            <div
              style={{
                fontSize: '10px',
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.ui
              }}
            >
              Archivo sugerido:
              <span style={{ color: THEME.colors.primaryAlt, marginLeft: '4px' }}>{pendingActionDetails.fileName}</span>
            </div>
          )}

          {pendingActionDetails?.branchName && (
            <div
              style={{
                fontSize: '10px',
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.ui
              }}
            >
              Sucursal:
              <span style={{ color: THEME.colors.text, marginLeft: '4px' }}>{pendingActionDetails.branchName}</span>
            </div>
          )}

          {pendingActionDetails?.summary && (
            <div
              style={{
                fontSize: '10px',
                color: THEME.colors.text,
                fontFamily: THEME.fonts.ui,
                lineHeight: '1.5'
              }}
            >
              {pendingActionDetails.summary}
            </div>
          )}

          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
            <button
              onClick={() => handleActionDecision(true)}
              disabled={isDecisionDisabled}
              style={{
                padding: '6px 14px',
                borderRadius: '4px',
                border: `1px solid ${THEME.colors.primary}60`,
                background: `linear-gradient(135deg, ${THEME.colors.primary}30, ${THEME.colors.primary}10)`,
                color: THEME.colors.primary,
                fontSize: '11px',
                fontFamily: THEME.fonts.ui,
                cursor: isDecisionDisabled ? 'not-allowed' : 'pointer',
                opacity: isDecisionDisabled ? 0.6 : 1,
                transition: 'all 0.2s ease'
              }}
            >
              Sí, guardar
            </button>
            <button
              onClick={() => handleActionDecision(false)}
              disabled={isDecisionDisabled}
              style={{
                padding: '6px 14px',
                borderRadius: '4px',
                border: '1px solid rgba(255, 107, 107, 0.5)',
                background: 'rgba(255, 107, 107, 0.12)',
                color: '#ff6b6b',
                fontSize: '11px',
                fontFamily: THEME.fonts.ui,
                cursor: isDecisionDisabled ? 'not-allowed' : 'pointer',
                opacity: isDecisionDisabled ? 0.6 : 1,
                transition: 'all 0.2s ease'
              }}
            >
              No, gracias
            </button>
          </div>

          {(actionSubmitting || loading) && (
            <div style={{ textAlign: 'right', fontSize: '9px', color: THEME.colors.textMuted }}>
              Registrando decisión...
            </div>
          )}
        </div>
      )}

      {/* Expert Alert Context Integration */}
      {alertContext && (
        <div style={{
          padding: '12px 20px',
          background: `
            linear-gradient(135deg,
              rgba(0, 255, 255, 0.08) 0%,
              rgba(0, 200, 255, 0.05) 50%,
              rgba(0, 255, 255, 0.08) 100%
            )
          `,
          borderTop: '1px solid rgba(0, 255, 255, 0.2)',
          borderBottom: '1px solid rgba(0, 255, 255, 0.2)',
          position: 'relative',
          zIndex: 3
        }}>
          {/* Alert context header */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            marginBottom: '8px'
          }}>
            <div style={{
              width: '6px',
              height: '6px',
              backgroundColor: THEME.colors.primary,
              borderRadius: '50%',
              boxShadow: `0 0 8px ${THEME.colors.primary}`,
              animation: 'pulse 1.5s infinite'
            }} />
            <span style={{
              fontSize: '10px',
              color: THEME.colors.primaryAlt,
              fontFamily: THEME.fonts.heading,
              letterSpacing: '0.1em',
              textTransform: 'uppercase'
            }}>
              Alert Context Available
            </span>
            <span style={{
              fontSize: '9px',
              color: THEME.colors.textMuted,
              fontFamily: THEME.fonts.ui,
              marginLeft: 'auto'
            }}>
              From: {alertContext.context?.agent || 'System'}
            </span>
          </div>

          {/* Alert context preview */}
          <div style={{
            background: 'rgba(0, 15, 30, 0.6)',
            border: '1px solid rgba(0, 255, 255, 0.15)',
            borderRadius: '4px',
            padding: '8px 10px',
            marginBottom: '10px',
            fontSize: '11px',
            color: THEME.colors.text,
            fontFamily: THEME.fonts.ui,
            lineHeight: '1.4',
            maxHeight: '60px',
            overflow: 'hidden',
            position: 'relative'
          }}>
            {alertContext.text}
            {alertContext.text.length > 120 && (
              <div style={{
                position: 'absolute',
                bottom: 0,
                right: 0,
                background: `linear-gradient(90deg, transparent, rgba(0, 15, 30, 0.9))`,
                padding: '0 8px',
                fontSize: '9px',
                color: THEME.colors.textMuted
              }}>
                ...
              </div>
            )}
          </div>

          {/* Action buttons */}
          <div style={{
            display: 'flex',
            gap: '8px',
            justifyContent: 'flex-end'
          }}>
            <button
              onClick={rejectAlertContext}
              style={{
                background: 'rgba(255, 107, 107, 0.1)',
                border: '1px solid rgba(255, 107, 107, 0.3)',
                borderRadius: '4px',
                padding: '4px 12px',
                fontSize: '10px',
                color: '#ff6b6b',
                fontFamily: THEME.fonts.ui,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'rgba(255, 107, 107, 0.15)';
                e.currentTarget.style.borderColor = 'rgba(255, 107, 107, 0.5)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'rgba(255, 107, 107, 0.1)';
                e.currentTarget.style.borderColor = 'rgba(255, 107, 107, 0.3)';
              }}
            >
              Dismiss
            </button>
            <button
              onClick={acceptAlertContext}
              style={{
                background: `linear-gradient(135deg, ${THEME.colors.primary}15, ${THEME.colors.primary}08)`,
                border: `1px solid ${THEME.colors.primary}40`,
                borderRadius: '4px',
                padding: '4px 12px',
                fontSize: '10px',
                color: THEME.colors.primary,
                fontFamily: THEME.fonts.ui,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: `0 0 8px ${THEME.colors.primary}20`
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = `linear-gradient(135deg, ${THEME.colors.primary}25, ${THEME.colors.primary}15)`;
                e.currentTarget.style.borderColor = `${THEME.colors.primary}60`;
                e.currentTarget.style.boxShadow = `0 0 12px ${THEME.colors.primary}30`;
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = `linear-gradient(135deg, ${THEME.colors.primary}15, ${THEME.colors.primary}08)`;
                e.currentTarget.style.borderColor = `${THEME.colors.primary}40`;
                e.currentTarget.style.boxShadow = `0 0 8px ${THEME.colors.primary}20`;
              }}
            >
              Use Context
            </button>
          </div>
        </div>
      )}

      {/* Premium neural input interface */}
      <div style={{
        padding: '16px 20px',
        background: `
          linear-gradient(135deg,
            rgba(0, 20, 40, 0.98) 0%,
            rgba(0, 15, 30, 0.98) 50%,
            rgba(0, 8, 17, 0.98) 100%
          )
        `,
        borderTop: '1px solid rgba(0, 255, 255, 0.3)',
        borderRadius: '0 0 6px 6px',
        position: 'relative'
      }}>
        {/* Premium accent border */}
        <div style={{
          position: 'absolute',
          top: 0,
          left: '20%',
          right: '20%',
          height: '1px',
          background: `
            linear-gradient(90deg,
              transparent 0%,
              rgba(0, 255, 255, 0.6) 50%,
              transparent 100%
            )
          `,
          boxShadow: '0 0 6px rgba(0, 255, 255, 0.4)'
        }} />

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}>
          <VoiceInterface sessionId={activeSessionId} onMessageAppend={handleVoiceMessageAppend} />

          {/* Input container with holographic effect */}
          <div style={{
            display: 'flex',
            alignItems: 'center',
            gap: '12px',
            background: alertContext
              ? `linear-gradient(135deg, ${THEME.colors.primary}08, ${THEME.colors.primary}04)`
              : `linear-gradient(135deg, rgba(0, 255, 255, 0.03) 0%, rgba(0, 200, 255, 0.02) 50%, rgba(0, 255, 255, 0.03) 100%)`,
            border: alertContext
              ? `1px solid ${THEME.colors.primary}50`
              : '1px solid rgba(0, 255, 255, 0.2)',
            borderRadius: '4px',
            padding: '8px 12px',
            boxShadow: alertContext
              ? `inset 0 1px 0 ${THEME.colors.primary}20, 0 2px 8px ${THEME.colors.primary}15, 0 0 12px ${THEME.colors.primary}10`
              : `inset 0 1px 0 rgba(0, 255, 255, 0.1), 0 2px 8px rgba(0, 255, 255, 0.05)`,
            fontFamily: "'JetBrains Mono', monospace",
            position: 'relative'
          }}>
            <div style={{
              width: '4px',
              height: '4px',
              backgroundColor: alertContext ? THEME.colors.primaryAlt : '#00ffff',
              borderRadius: '50%',
              boxShadow: `0 0 6px ${alertContext ? THEME.colors.primaryAlt : '#00ffff'}`,
              animation: loading ? 'pulse 1s infinite' : alertContext ? 'alertPulse 1.5s infinite' : 'none'
            }} />

            {/* Context Source Indicator */}
            {alertContext && (
              <div style={{
                fontSize: '8px',
                color: THEME.colors.primaryAlt,
                fontFamily: THEME.fonts.ui,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
                opacity: 0.8,
                display: 'flex',
                alignItems: 'center',
                gap: '4px'
              }}>
                <div style={{
                  width: '2px',
                  height: '2px',
                  backgroundColor: THEME.colors.primaryAlt,
                  borderRadius: '50%'
                }} />
                {alertContext.context?.agent}
              </div>
            )}

            {/* Input field */}
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder={alertContext ? "Edit context and send..." : ""}
              disabled={loading}
              className={alertContext ? 'context-active' : ''}
              style={{
                flex: 1,
                background: 'transparent',
                border: 'none',
                outline: 'none',
                color: alertContext ? THEME.colors.primaryAlt : '#e6f1ff',
                fontSize: '11px',
                fontFamily: THEME.fonts.heading,
                letterSpacing: '0.05em',
                padding: '2px 0',
                textShadow: alertContext
                  ? `0 0 6px ${THEME.colors.primaryAlt}40`
                  : '0 0 4px rgba(230, 241, 255, 0.3)'
              }}
            />

            {loading && (
              <div style={{
                width: '2px',
                height: '8px',
                background: 'linear-gradient(to top, transparent, #00ffff)',
                animation: 'dataFlow 1s ease-in-out infinite'
              }} />
            )}
          </div>
        </div>
      </div>

      <style>{`
        /* Premium scrollbar */
        div::-webkit-scrollbar {
          width: 6px;
        }
        div::-webkit-scrollbar-track {
          background: transparent;
        }
        div::-webkit-scrollbar-thumb {
          background: linear-gradient(
            to bottom,
            rgba(0, 255, 255, 0.4),
            rgba(0, 200, 255, 0.3),
            rgba(0, 255, 255, 0.4)
          );
          border-radius: 3px;
          box-shadow: 0 0 4px rgba(0, 255, 255, 0.2);
        }
        div::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(
            to bottom,
            rgba(0, 255, 255, 0.6),
            rgba(0, 200, 255, 0.5),
            rgba(0, 255, 255, 0.6)
          );
          box-shadow: 0 0 8px rgba(0, 255, 255, 0.4);
        }

        /* Premium animations */
        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.6;
            transform: scale(0.95);
          }
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes ping {
          75%, 100% {
            transform: scale(2);
            opacity: 0;
          }
        }

        @keyframes rotate {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        @keyframes dataFlow {
          0% {
            transform: translateY(-100%);
            opacity: 0;
          }
          10% {
            opacity: 0.8;
          }
          90% {
            opacity: 0.8;
          }
          100% {
            transform: translateY(100vh);
            opacity: 0;
          }
        }

        @keyframes alertPulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
            box-shadow: 0 0 6px ${THEME.colors.primaryAlt};
          }
          50% {
            opacity: 0.7;
            transform: scale(1.2);
            box-shadow: 0 0 12px ${THEME.colors.primaryAlt}, 0 0 20px ${THEME.colors.primaryAlt}40;
          }
        }

        @keyframes contextPulse {
          0%, 100% {
            opacity: 0.8;
            box-shadow: 0 0 8px ${THEME.colors.primary}20;
          }
          50% {
            opacity: 1;
            box-shadow: 0 0 12px ${THEME.colors.primary}30, 0 0 20px ${THEME.colors.primary}15;
          }
        }

        /* Premium input styling */
        input::placeholder {
          color: rgba(0, 255, 255, 0.4);
          font-style: italic;
        }

        input:focus::placeholder {
          color: rgba(0, 255, 255, 0.6);
        }

        /* Context-aware placeholder styling */
        input.context-active::placeholder {
          color: ${THEME.colors.primaryAlt}80;
          font-style: normal;
          font-weight: 500;
        }

        /* Glow effect for focused elements */
        input:focus {
          text-shadow: 0 0 8px rgba(230, 241, 255, 0.5) !important;
        }
      `}</style>
    </div>
  );
}

