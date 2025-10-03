import React from 'react';
import { CHAT_THEME } from '../chatTheme';

interface MessageBubbleProps {
  message: {
    id: string;
    sender: 'user' | 'bot';
    text: string;
    agent?: string;
    timestamp: number;
  };
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.sender === 'user';

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  return (
    <div style={{
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
              background: `linear-gradient(135deg, ${CHAT_THEME.colors.primary}, ${CHAT_THEME.colors.primaryAlt})`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '8px',
              fontFamily: CHAT_THEME.fonts.heading,
              color: CHAT_THEME.colors.bg,
              flexShrink: 0,
              boxShadow: `0 0 8px ${CHAT_THEME.colors.primary}30`
            }}>
              C
            </div>
            <span style={{
              fontSize: '11px',
              color: CHAT_THEME.colors.textMuted,
              fontFamily: CHAT_THEME.fonts.ui,
              letterSpacing: '0.05em'
            }}>
              CAPI
            </span>
          </>
        )}

        <div style={{
          fontSize: '10px',
          color: CHAT_THEME.colors.textMuted + '80',
          fontFamily: CHAT_THEME.fonts.ui,
          marginLeft: isUser ? '0' : 'auto',
          marginRight: isUser ? 'auto' : '0'
        }}>
          {formatTime(message.timestamp)}
        </div>

        {isUser && (
          <>
            <span style={{
              fontSize: '11px',
              color: CHAT_THEME.colors.textMuted,
              fontFamily: CHAT_THEME.fonts.ui,
              letterSpacing: '0.05em'
            }}>
              You
            </span>
            <div style={{
              width: '20px',
              height: '20px',
              borderRadius: '4px',
              background: `linear-gradient(135deg, ${CHAT_THEME.colors.textMuted}, ${CHAT_THEME.colors.textMuted}80)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '8px',
              fontFamily: CHAT_THEME.fonts.heading,
              color: CHAT_THEME.colors.bg,
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
            ? `linear-gradient(135deg, ${CHAT_THEME.colors.primary}12, ${CHAT_THEME.colors.primary}08)`
            : CHAT_THEME.colors.panel,
          border: `1px solid ${isUser ? CHAT_THEME.colors.primary + '25' : CHAT_THEME.colors.border}`,
          borderRadius: '12px',
          color: CHAT_THEME.colors.text,
          fontFamily: CHAT_THEME.fonts.ui,
          fontSize: '13px',
          lineHeight: '1.5',
          boxShadow: isUser
            ? `0 2px 12px ${CHAT_THEME.colors.primary}15`
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
            border: `1px solid ${isUser ? CHAT_THEME.colors.primary + '40' : CHAT_THEME.colors.border}`,
            borderRadius: '1px',
            [isUser ? 'borderLeft' : 'borderRight']: 'none',
            [isUser ? 'borderBottom' : 'borderBottom']: 'none'
          }} />

          {message.text}
        </div>
      </div>
    </div>
  );
}