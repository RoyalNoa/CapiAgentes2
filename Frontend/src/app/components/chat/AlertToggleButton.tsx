"use client";

import React from 'react';

type AlertToggleButtonPosition = 'top-left' | 'bottom-right';

const THEME = {
  colors: {
    primary: '#00e5ff',
    primaryAlt: '#7df9ff',
    warning: '#ffcc00',
    text: '#e6f1ff',
    textMuted: '#8aa0c5',
    bg: '#0a0f1c',
    panel: 'rgba(14, 22, 38, 0.85)',
    border: '#1d2b4a'
  },
  fonts: {
    heading: "'Orbitron', ui-sans-serif, system-ui, sans-serif",
    ui: "'Inter', ui-sans-serif, system-ui, sans-serif"
  }
} as const;

interface AlertToggleButtonProps {
  onClick: () => void;
  alertCount: number;
  criticalCount?: number;
  isActive: boolean;
  position?: AlertToggleButtonPosition;
}

export default function AlertToggleButton({
  onClick,
  alertCount,
  criticalCount = 0,
  isActive,
  position = 'top-left'
}: AlertToggleButtonProps) {
  const hasAlerts = alertCount > 0;
  const hasCritical = criticalCount > 0;
  const pulseColor = hasCritical ? THEME.colors.warning : THEME.colors.primary;

  const positionStyle: React.CSSProperties =
    position === 'bottom-right'
      ? { bottom: '20px', right: '90px' }
      : { top: '15px', left: '20px' };

  const restingShadow = `0 8px 32px rgba(0, 0, 0, 0.4), 0 0 20px ${pulseColor}25, inset 0 1px 0 rgba(255, 255, 255, 0.1)`;
  const hoverShadow = `0 12px 48px rgba(0, 0, 0, 0.5), 0 0 30px ${pulseColor}35, inset 0 1px 0 rgba(255, 255, 255, 0.15)`;

  const baseStyle: React.CSSProperties = {
    position: 'fixed',
    ...positionStyle,
    width: '56px',
    height: '56px',
    borderRadius: '16px',
    border: `1px solid ${THEME.colors.border}`,
    background: `linear-gradient(135deg, ${THEME.colors.panel} 0%, rgba(14, 22, 38, 0.95) 100%)`,
    boxShadow: restingShadow,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1080,
    backdropFilter: 'blur(8px)',
    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
    animation: hasAlerts ? 'alertPulse 2s infinite' : 'none',
    transform: isActive ? 'scale(0.95)' : 'scale(1)'
  };

  return (
    <button
      onClick={onClick}
      style={baseStyle}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'scale(1.05)';
        e.currentTarget.style.boxShadow = hoverShadow;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = isActive ? 'scale(0.95)' : 'scale(1)';
        e.currentTarget.style.boxShadow = restingShadow;
      }}
    >
      <div style={{
        position: 'absolute',
        top: '4px',
        left: '4px',
        width: '8px',
        height: '8px',
        border: `1px solid ${THEME.colors.primary}60`,
        borderRight: 'none',
        borderBottom: 'none',
        borderRadius: '2px 0 0 0'
      }} />
      <div style={{
        position: 'absolute',
        top: '4px',
        right: '4px',
        width: '8px',
        height: '8px',
        border: `1px solid ${THEME.colors.primary}60`,
        borderLeft: 'none',
        borderBottom: 'none',
        borderRadius: '0 2px 0 0'
      }} />

      {hasCritical && (
        <span style={{
          position: 'absolute',
          top: '10px',
          left: '10px',
          width: '8px',
          height: '8px',
          borderRadius: '50%',
          background: THEME.colors.warning,
          boxShadow: `0 0 8px ${THEME.colors.warning}`
        }} />
      )}

      <div style={{
        position: 'relative',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          style={{ filter: `drop-shadow(0 0 6px ${pulseColor}40)` }}
        >
          <path
            d="M12 2C13.1 2 14 2.9 14 4C14 4.1 14 4.2 14 4.3C16.3 5.2 18 7.4 18 10V16L20 18V19H4V18L6 16V10C6 7.4 7.7 5.2 10 4.3C10 4.2 10 4.1 10 4C10 2.9 10.9 2 12 2ZM10 21C10 22.1 10.9 23 12 23C13.1 23 14 22.1 14 21H10Z"
            fill={hasAlerts ? THEME.colors.primaryAlt : THEME.colors.primary}
          />
        </svg>

        {alertCount > 0 && (
          <div style={{
            position: 'absolute',
            top: '-6px',
            right: '-6px',
            minWidth: '18px',
            height: '18px',
            borderRadius: '9px',
            background: `linear-gradient(135deg, ${THEME.colors.primary}, ${THEME.colors.primaryAlt})`,
            color: THEME.colors.bg,
            fontSize: '10px',
            fontWeight: 700,
            fontFamily: THEME.fonts.heading,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            border: `2px solid ${THEME.colors.panel}`,
            boxShadow: `0 0 12px ${THEME.colors.primary}60`,
            animation: 'bounce 1s infinite'
          }}>
            {alertCount > 99 ? '99+' : alertCount}
          </div>
        )}
      </div>

      <style jsx>{`
        @keyframes alertPulse {
          0%, 100% {
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                        0 0 22px ${pulseColor}25,
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
          }
          50% {
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4),
                        0 0 36px ${pulseColor}40,
                        inset 0 1px 0 rgba(255, 255, 255, 0.1);
          }
        }

        @keyframes bounce {
          0%, 20%, 53%, 80%, 100% {
            transform: translateY(0);
          }
          40%, 43% {
            transform: translateY(-3px);
          }
          70% {
            transform: translateY(-1px);
          }
          90% {
            transform: translateY(-1px);
          }
        }
      `}</style>
    </button>
  );
}
