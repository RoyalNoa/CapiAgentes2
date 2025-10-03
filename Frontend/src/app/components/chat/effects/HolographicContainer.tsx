import React from 'react';
import { CHAT_THEME } from '../chatTheme';

interface HolographicContainerProps {
  children: React.ReactNode;
  className?: string;
}

export default function HolographicContainer({ children, className = '' }: HolographicContainerProps) {
  return (
    <div
      className={className}
      style={{
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
        fontFamily: CHAT_THEME.fonts.ui,
        position: 'relative',
        backdropFilter: 'blur(8px)'
      }}
    >
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

      {children}
    </div>
  );
}