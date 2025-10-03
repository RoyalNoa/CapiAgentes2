import React from 'react';
import { CHAT_THEME } from '../chatTheme';

interface ChatHeaderProps {
  connection: { status: 'idle' | 'connecting' | 'open' | 'reconnecting' | 'failed' | 'closed' };
  alertContext?: {
    text: string;
    context: any;
  } | null;
}

export default function ChatHeader({ connection, alertContext }: ChatHeaderProps) {
  return (
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
              color: CHAT_THEME.colors.primaryAlt,
              fontSize: '11px',
              fontWeight: 700,
              letterSpacing: '0.15em',
              textTransform: 'uppercase',
              fontFamily: CHAT_THEME.fonts.heading,
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
            background: `linear-gradient(135deg, ${CHAT_THEME.colors.primary}20, ${CHAT_THEME.colors.primary}10)`,
            border: `1px solid ${CHAT_THEME.colors.primary}40`,
            borderRadius: '4px',
            fontSize: '9px',
            color: CHAT_THEME.colors.primary,
            fontFamily: CHAT_THEME.fonts.ui,
            letterSpacing: '0.05em',
            textTransform: 'uppercase',
            boxShadow: `0 0 8px ${CHAT_THEME.colors.primary}20`,
            animation: 'contextPulse 2s infinite'
          }}>
            <div style={{
              width: '4px',
              height: '4px',
              backgroundColor: CHAT_THEME.colors.primary,
              borderRadius: '50%',
              boxShadow: `0 0 4px ${CHAT_THEME.colors.primary}`,
              animation: 'pulse 1s infinite'
            }} />
            Context: {alertContext.context?.agent || 'Alert'}
          </div>
        )}
      </div>
    </div>
  );
}