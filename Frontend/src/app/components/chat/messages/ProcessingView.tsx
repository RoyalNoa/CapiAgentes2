import React from 'react';
import { CHAT_THEME } from '../chatTheme';

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

interface ProcessingViewProps {
  visible: boolean;
  processingMessage?: ProcessingMessage | null;
}

export default function ProcessingView({ visible, processingMessage }: ProcessingViewProps) {
  if (!visible || !processingMessage) return null;

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderTaskStep = (task: TaskStep, index: number) => {
    const getStatusConfig = () => {
      switch (task.status) {
        case 'complete':
          return {
            icon: '●',
            color: CHAT_THEME.colors.success,
            bgColor: CHAT_THEME.colors.success + '15',
            borderColor: CHAT_THEME.colors.success + '30'
          };
        case 'running':
          return {
            icon: '●',
            color: CHAT_THEME.colors.primary,
            bgColor: CHAT_THEME.colors.primary + '15',
            borderColor: CHAT_THEME.colors.primary + '40'
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
            color: CHAT_THEME.colors.textMuted,
            bgColor: 'transparent',
            borderColor: CHAT_THEME.colors.textMuted + '20'
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
          fontFamily: CHAT_THEME.fonts.ui,
          color: CHAT_THEME.colors.text,
          flex: 1
        }}>
          {task.text}
        </span>
      </div>
    );
  };

  return (
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
          background: `linear-gradient(135deg, ${CHAT_THEME.colors.primary}, ${CHAT_THEME.colors.primaryAlt})`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '8px',
          fontFamily: CHAT_THEME.fonts.heading,
          color: CHAT_THEME.colors.bg,
          flexShrink: 0,
          boxShadow: `0 0 12px ${CHAT_THEME.colors.primary}40`,
          animation: 'pulse 1.5s infinite'
        }}>
          C
        </div>
        <span style={{
          fontSize: '11px',
          color: CHAT_THEME.colors.textMuted,
          fontFamily: CHAT_THEME.fonts.ui,
          letterSpacing: '0.05em'
        }}>
          CAPI is thinking...
        </span>
        <div style={{
          fontSize: '10px',
          color: CHAT_THEME.colors.textMuted + '80',
          fontFamily: CHAT_THEME.fonts.ui,
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
          background: CHAT_THEME.colors.panel,
          border: `1px solid ${CHAT_THEME.colors.border}`,
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
            border: `1px solid ${CHAT_THEME.colors.border}`,
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
  );
}