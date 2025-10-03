/**
 * Ruta: Frontend/src/app/components/Graph/AnimatedEdge.tsx
 * Descripción: Arista animada con estética HUD (glow y dash animado) para el grafo de agentes.
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 * Referencias: AI/estandares.md
 */
'use client';

import React, { useEffect, useState } from 'react';

const hashEdgeCoordinates = (x1: number, y1: number, x2: number, y2: number): number => {
  const prime = 16777619;
  let hash = 2166136261;
  for (const value of [x1, y1, x2, y2]) {
    hash ^= Math.floor(value * 1000);
    hash *= prime;
    hash >>>= 0;
  }
  return hash >>> 0;
};

const getDeterministicDelay = (x1: number, y1: number, x2: number, y2: number, maxMs: number): string => {
  const hash = hashEdgeCoordinates(x1, y1, x2, y2);
  const range = Math.max(1, maxMs);
  const delay = hash % range;
  return `${delay}ms`;
};


interface AnimatedEdgeProps {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  isAnimating?: boolean;
  strokeColor?: string;
  strokeWidth?: number;
  duration?: number;
  isDashed?: boolean;
  intensity?: 'low' | 'medium' | 'high';
  direction?: 'forward' | 'backward' | 'bidirectional';
  isActive?: boolean;
}

export default function AnimatedEdge({
  x1,
  y1,
  x2,
  y2,
  isAnimating = false,
  strokeColor = 'rgba(125, 249, 255, 0.6)',
  strokeWidth = 2,
  duration = 2000,
  isDashed = true, // Always dashed by default
  intensity = 'medium',
  direction = 'forward',
  isActive = false
}: AnimatedEdgeProps) {
  const [animationKey, setAnimationKey] = useState(0);

  useEffect(() => {
    if (isAnimating) {
      setAnimationKey(prev => prev + 1);
    }
  }, [isAnimating]);

  // Always use dashed pattern - expert approach with varied patterns
  const getStrokeDasharray = () => {
    if (!isDashed) return '8,4'; // Even when not explicitly dashed
    switch (intensity) {
      case 'high': return '12,6';
      case 'medium': return '8,4';
      case 'low': return '6,3';
      default: return '8,4';
    }
  };

  const strokeDasharray = getStrokeDasharray();
  const baseOpacity = isActive ? 0.8 : 0.4;
  const glowIntensity = intensity === 'high' ? 1.2 : intensity === 'medium' ? 1.0 : 0.8;

  return (
    <g>
      {/* Background glow */}
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={strokeColor}
        strokeWidth={strokeWidth + 2}
        strokeDasharray={strokeDasharray}
        opacity={baseOpacity * 0.3 * glowIntensity}
        style={{
          filter: `blur(2px) drop-shadow(0 0 ${8 * glowIntensity}px ${strokeColor})`,
          pointerEvents: 'none'
        }}
      />

      {/* Main static edge - always dashed */}
      <line
        x1={x1}
        y1={y1}
        x2={x2}
        y2={y2}
        stroke={strokeColor}
        strokeWidth={strokeWidth}
        strokeDasharray={strokeDasharray}
        opacity={baseOpacity}
        style={{
          filter: `drop-shadow(0 0 ${4 * glowIntensity}px rgba(0,229,255,${0.3 * glowIntensity}))`,
          transition: 'opacity 0.3s ease'
        }}
      />

      {/* Subtle pulse for idle connections */}
      {!isAnimating && isActive && (
        <line
          x1={x1}
          y1={y1}
          x2={x2}
          y2={y2}
          stroke={strokeColor}
          strokeWidth={strokeWidth}
          strokeDasharray={strokeDasharray}
          opacity={0.3}
          style={{
            animation: `idle-pulse ${duration * 2}ms ease-in-out infinite`,
            animation: `idle-pulse ${duration * 2}ms ease-in-out infinite`,
            animationDelay: getDeterministicDelay(x1, y1, x2, y2, 1000)
          }}
        />
      )}

      {/* Active data flow animation */}
      {isAnimating && (
        <>
          {/* Primary flow */}
          <line
            key={`primary-${animationKey}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="rgba(0,229,255,0.95)"
            strokeWidth={strokeWidth + 0.5}
            strokeDasharray={`${12 * glowIntensity},${8 * glowIntensity}`}
            opacity={0.9}
            style={{
              animation: `data-flow-${direction} ${duration}ms linear infinite`,
              filter: `drop-shadow(0 0 ${6 * glowIntensity}px rgba(0,229,255,0.8))`
            }}
          />

          {/* Secondary particles */}
          <line
            key={`particles-${animationKey}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke="rgba(125,249,255,0.7)"
            strokeWidth={strokeWidth * 0.6}
            strokeDasharray={`${6 * glowIntensity},${12 * glowIntensity}`}
            opacity={0.6}
            style={{
              animation: `particle-flow-${direction} ${duration * 0.7}ms linear infinite`,
              animationDelay: `${duration * 0.3}ms`
            }}
          />

          {/* Bidirectional flow if needed */}
          {direction === 'bidirectional' && (
            <line
              key={`bidirectional-${animationKey}`}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="rgba(255,204,0,0.7)"
              strokeWidth={strokeWidth * 0.8}
              strokeDasharray={`${8 * glowIntensity},${6 * glowIntensity}`}
              opacity={0.5}
              style={{
                animation: `data-flow-backward ${duration * 1.2}ms linear infinite`,
                animationDelay: `${duration * 0.5}ms`
              }}
            />
          )}
        </>
      )}

      <style jsx>{`
        @keyframes data-flow-forward {
          0% {
            stroke-dashoffset: 20;
            opacity: 0.95;
          }
          100% {
            stroke-dashoffset: -20;
            opacity: 0.4;
          }
        }

        @keyframes data-flow-backward {
          0% {
            stroke-dashoffset: -20;
            opacity: 0.95;
          }
          100% {
            stroke-dashoffset: 20;
            opacity: 0.4;
          }
        }

        @keyframes particle-flow-forward {
          0% {
            stroke-dashoffset: 18;
            opacity: 0.7;
          }
          100% {
            stroke-dashoffset: -18;
            opacity: 0.2;
          }
        }

        @keyframes particle-flow-backward {
          0% {
            stroke-dashoffset: -18;
            opacity: 0.7;
          }
          100% {
            stroke-dashoffset: 18;
            opacity: 0.2;
          }
        }

        @keyframes idle-pulse {
          0%, 100% {
            opacity: 0.2;
          }
          50% {
            opacity: 0.5;
          }
        }
      `}</style>
    </g>
  );
}
