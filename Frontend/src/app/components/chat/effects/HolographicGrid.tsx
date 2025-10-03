import React from 'react';

interface HolographicGridProps {
  opacity?: number;
  animated?: boolean;
}

export default function HolographicGrid({ opacity = 0.6, animated = true }: HolographicGridProps) {
  return (
    <>
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
        opacity
      }} />

      {/* Flowing data streams */}
      {animated && (
        <>
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
        </>
      )}
    </>
  );
}