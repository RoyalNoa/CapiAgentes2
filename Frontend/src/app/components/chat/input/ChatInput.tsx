import React, { useState, useCallback } from 'react';
import { CHAT_THEME } from '../chatTheme';

interface ChatInputProps {
  onSend: (text: string) => Promise<void>;
  loading: boolean;
  alertContext?: {
    text: string;
    context: any;
  } | null;
  onAcceptContext?: () => void;
  onRejectContext?: () => void;
}

export default function ChatInput({
  onSend,
  loading,
  alertContext,
  onAcceptContext,
  onRejectContext
}: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const inputToSend = input;
    setInput('');

    try {
      await onSend(inputToSend);
    } catch (error: any) {
      setInput(inputToSend);
    }
  }, [input, loading, onSend]);

  const handleInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [handleSend]);

  return (
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

      {/* Alert Context */}
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
          zIndex: 3,
          marginBottom: '12px'
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
              backgroundColor: CHAT_THEME.colors.primary,
              borderRadius: '50%',
              boxShadow: `0 0 8px ${CHAT_THEME.colors.primary}`,
              animation: 'pulse 1.5s infinite'
            }} />
            <span style={{
              fontSize: '10px',
              color: CHAT_THEME.colors.primaryAlt,
              fontFamily: CHAT_THEME.fonts.heading,
              letterSpacing: '0.1em',
              textTransform: 'uppercase'
            }}>
              Alert Context Available
            </span>
            <span style={{
              fontSize: '9px',
              color: CHAT_THEME.colors.textMuted,
              fontFamily: CHAT_THEME.fonts.ui,
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
            color: CHAT_THEME.colors.text,
            fontFamily: CHAT_THEME.fonts.ui,
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
                color: CHAT_THEME.colors.textMuted
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
              onClick={onRejectContext}
              style={{
                background: 'rgba(255, 107, 107, 0.1)',
                border: '1px solid rgba(255, 107, 107, 0.3)',
                borderRadius: '4px',
                padding: '4px 12px',
                fontSize: '10px',
                color: '#ff6b6b',
                fontFamily: CHAT_THEME.fonts.ui,
                cursor: 'pointer',
                transition: 'all 0.2s ease'
              }}
            >
              Dismiss
            </button>
            <button
              onClick={onAcceptContext}
              style={{
                background: `linear-gradient(135deg, ${CHAT_THEME.colors.primary}15, ${CHAT_THEME.colors.primary}08)`,
                border: `1px solid ${CHAT_THEME.colors.primary}40`,
                borderRadius: '4px',
                padding: '4px 12px',
                fontSize: '10px',
                color: CHAT_THEME.colors.primary,
                fontFamily: CHAT_THEME.fonts.ui,
                cursor: 'pointer',
                transition: 'all 0.2s ease',
                boxShadow: `0 0 8px ${CHAT_THEME.colors.primary}20`
              }}
            >
              Use Context
            </button>
          </div>
        </div>
      )}

      {/* Input container with holographic effect */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        background: alertContext
          ? `linear-gradient(135deg, ${CHAT_THEME.colors.primary}08, ${CHAT_THEME.colors.primary}04)`
          : `linear-gradient(135deg, rgba(0, 255, 255, 0.03) 0%, rgba(0, 200, 255, 0.02) 50%, rgba(0, 255, 255, 0.03) 100%)`,
        border: alertContext
          ? `1px solid ${CHAT_THEME.colors.primary}50`
          : '1px solid rgba(0, 255, 255, 0.2)',
        borderRadius: '4px',
        padding: '8px 12px',
        boxShadow: alertContext
          ? `inset 0 1px 0 ${CHAT_THEME.colors.primary}20, 0 2px 8px ${CHAT_THEME.colors.primary}15, 0 0 12px ${CHAT_THEME.colors.primary}10`
          : `inset 0 1px 0 rgba(0, 255, 255, 0.1), 0 2px 8px rgba(0, 255, 255, 0.05)`,
        fontFamily: "'JetBrains Mono', monospace",
        position: 'relative'
      }}>
        <div style={{
          width: '4px',
          height: '4px',
          backgroundColor: alertContext ? CHAT_THEME.colors.primaryAlt : '#00ffff',
          borderRadius: '50%',
          boxShadow: `0 0 6px ${alertContext ? CHAT_THEME.colors.primaryAlt : '#00ffff'}`,
          animation: loading ? 'pulse 1s infinite' : alertContext ? 'alertPulse 1.5s infinite' : 'none'
        }} />

        {/* Context Source Indicator */}
        {alertContext && (
          <div style={{
            fontSize: '8px',
            color: CHAT_THEME.colors.primaryAlt,
            fontFamily: CHAT_THEME.fonts.ui,
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
              backgroundColor: CHAT_THEME.colors.primaryAlt,
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
            color: alertContext ? CHAT_THEME.colors.primaryAlt : '#e6f1ff',
            fontSize: '11px',
            fontFamily: CHAT_THEME.fonts.heading,
            letterSpacing: '0.05em',
            padding: '2px 0',
            textShadow: alertContext
              ? `0 0 6px ${CHAT_THEME.colors.primaryAlt}40`
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
  );
}