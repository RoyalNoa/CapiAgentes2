/**
 * Ruta: Frontend/src/app/components/HUD/ProgressIndicator.tsx
 * Descripción: Indicador de progreso avanzado con efectos HUD para estados del sistema
 * Estado: Activo
 * Autor: Claude Code
 * Última actualización: 2025-09-14
 * Tareas relacionadas: PantallaAgentes-HUD-Enhancement
 * Referencias: AI/estandares.md
 */

'use client';

import React from 'react';

interface ProgressIndicatorProps {
  label: string;
  value: number;
  max?: number;
  unit?: string;
  variant?: 'default' | 'success' | 'warning' | 'error' | 'accent';
  size?: 'sm' | 'md' | 'lg';
  showValue?: boolean;
  animated?: boolean;
  className?: string;
}

export default function ProgressIndicator({
  label,
  value,
  max = 100,
  unit = '%',
  variant = 'default',
  size = 'md',
  showValue = true,
  animated = true,
  className = ''
}: ProgressIndicatorProps) {
  const percentage = Math.min(100, Math.max(0, (value / max) * 100));

  const getVariantColors = (variant: string) => {
    switch (variant) {
      case 'success':
        return {
          track: 'rgba(16, 185, 129, 0.2)',
          fill: '#10b981',
          glow: 'rgba(16, 185, 129, 0.4)',
          text: '#10b981'
        };
      case 'warning':
        return {
          track: 'rgba(245, 158, 11, 0.2)',
          fill: '#f59e0b',
          glow: 'rgba(245, 158, 11, 0.4)',
          text: '#f59e0b'
        };
      case 'error':
        return {
          track: 'rgba(239, 68, 68, 0.2)',
          fill: '#ef4444',
          glow: 'rgba(239, 68, 68, 0.4)',
          text: '#ef4444'
        };
      case 'accent':
        return {
          track: 'rgba(0, 229, 255, 0.2)',
          fill: 'var(--hud-accent)',
          glow: 'rgba(0, 229, 255, 0.4)',
          text: 'var(--hud-accent)'
        };
      default:
        return {
          track: 'rgba(125, 249, 255, 0.2)',
          fill: 'rgba(125, 249, 255, 0.8)',
          glow: 'rgba(125, 249, 255, 0.3)',
          text: 'rgba(125, 249, 255, 0.9)'
        };
    }
  };

  const getSizeStyles = (size: string) => {
    switch (size) {
      case 'sm':
        return { height: '6px', fontSize: '0.75rem' };
      case 'lg':
        return { height: '12px', fontSize: '0.875rem' };
      default:
        return { height: '8px', fontSize: '0.8rem' };
    }
  };

  const colors = getVariantColors(variant);
  const sizeStyles = getSizeStyles(size);

  return (
    <div className={`space-y-2 ${className}`}>
      {/* Label and value */}
      <div className="flex justify-between items-center">
        <span
          className="font-medium tracking-wide uppercase"
          style={{ fontSize: sizeStyles.fontSize, color: colors.text }}
        >
          {label}
        </span>
        {showValue && (
          <span
            className="font-mono"
            style={{ fontSize: sizeStyles.fontSize, color: colors.text }}
          >
            {Math.round(value)}{unit}
          </span>
        )}
      </div>

      {/* Progress track */}
      <div
        className="rounded-sm overflow-hidden relative"
        style={{
          height: sizeStyles.height,
          backgroundColor: colors.track,
          border: `1px solid ${colors.fill}30`
        }}
      >
        {/* Progress fill */}
        <div
          className={`h-full transition-all duration-1000 ease-out relative ${animated ? 'animate-pulse' : ''}`}
          style={{
            width: `${percentage}%`,
            background: `linear-gradient(90deg, ${colors.fill}, ${colors.fill}cc)`,
            boxShadow: `0 0 8px ${colors.glow}, inset 0 1px 0 rgba(255,255,255,0.1)`
          }}
        >
          {/* Animated overlay */}
          {animated && (
            <div
              className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
              style={{
                animation: 'progress-shimmer 2s infinite linear'
              }}
            />
          )}
        </div>

        {/* Progress indicator line */}
        {percentage > 0 && (
          <div
            className="absolute top-0 w-0.5 h-full"
            style={{
              left: `${percentage}%`,
              background: colors.fill,
              boxShadow: `0 0 4px ${colors.glow}`
            }}
          />
        )}
      </div>

      <style jsx>{`
        @keyframes progress-shimmer {
          0% {
            transform: translateX(-100%);
          }
          100% {
            transform: translateX(100%);
          }
        }
      `}</style>
    </div>
  );
}