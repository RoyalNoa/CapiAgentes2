/**
 * Ruta: Frontend/src/app/components/Graph/GraphNode.tsx
 * Descripción: Nodo del grafo con estilos HUD (Ironman). Estados visuales, hover y accesibilidad.
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 * Referencias: AI/estandares.md
 */

'use client';

import React, { useState } from 'react';


const hashString = (value: string): number => {
  let hash = 0;
  for (let i = 0; i < value.length; i += 1) {
    hash = (hash * 31 + value.charCodeAt(i)) >>> 0;
  }
  return hash;
};

const getIdleAnimationDelay = (nodeId: string): string => {
  const hash = hashString(nodeId);
  const seconds = (hash % 2000) / 1000;
  return `${seconds}s`;
};
type NodeStatus = 'idle' | 'running' | 'success' | 'error' | 'disabled';

interface GraphNodeProps {
  id: string;
  label: string;
  x: number;
  y: number;
  width?: number;
  height?: number;
  status?: NodeStatus;
  isAgent?: boolean;
  enabled?: boolean;
  onClick?: (nodeId: string) => void;
  onHover?: (nodeId: string, isHovering: boolean) => void;
  className?: string;
}

export default function GraphNode({
  id,
  label,
  x,
  y,
  width = 200,
  height = 60,
  status = 'idle',
  isAgent = false,
  enabled = true,
  onClick,
  onHover,
  className = ''
}: GraphNodeProps) {
  const [isHovering, setIsHovering] = useState(false);

  const getNodeColor = (nodeStatus: NodeStatus, isEnabled: boolean): string => {
    if (!isEnabled) return 'var(--node-disabled)';
    switch (nodeStatus) {
      case 'running':
        return 'var(--node-running)';
      case 'success':
        return 'var(--node-success)';
      case 'error':
        return 'var(--node-error)';
      default:
        return 'var(--node-idle)';
    }
  };

  const getSecondaryColor = (nodeStatus: NodeStatus, isEnabled: boolean): string => {
    if (!isEnabled) return 'var(--node-disabled-secondary)';
    switch (nodeStatus) {
      case 'running':
        return 'var(--node-running-secondary)';
      case 'success':
        return 'var(--node-success-secondary)';
      case 'error':
        return 'var(--node-error-secondary)';
      default:
        return 'var(--node-idle-secondary)';
    }
  };

  const getShadowIntensity = (nodeStatus: NodeStatus): number => {
    switch (nodeStatus) {
      case 'running': return 1.0;
      case 'success': return 0.8;
      case 'error': return 0.9;
      default: return 0.6;
    }
  };

  const getTextColor = (nodeStatus: NodeStatus, isEnabled: boolean): string => {
    if (!isEnabled) return '#b7c4e2';
    return nodeStatus === 'idle' ? 'var(--node-label)' : '#eaf6ff';
  };

  const handleClick = () => {
    onClick?.(id);
  };

  const handleMouseEnter = () => {
    setIsHovering(true);
    onHover?.(id, true);
  };

  const handleMouseLeave = () => {
    setIsHovering(false);
    onHover?.(id, false);
  };

  const fillColor = getNodeColor(status, enabled);
  const secondaryColor = getSecondaryColor(status, enabled);
  const textColor = getTextColor(status, enabled);
  const shadowIntensity = getShadowIntensity(status);

  return (
    <g className={className}>
      {/* Advanced gradients and filters */}
      <defs>
        {/* Primary gradient */}
        <linearGradient id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={fillColor} stopOpacity={0.95} />
          <stop offset="50%" stopColor={fillColor} stopOpacity={0.85} />
          <stop offset="100%" stopColor={secondaryColor} stopOpacity={0.7} />
        </linearGradient>

        {/* Border gradient */}
        <linearGradient id={`border-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={fillColor} stopOpacity={0.8} />
          <stop offset="100%" stopColor={fillColor} stopOpacity={0.3} />
        </linearGradient>

        {/* Glow filter */}
        <filter id={`glow-${id}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="4" result="coloredBlur"/>
          <feMerge>
            <feMergeNode in="coloredBlur"/>
            <feMergeNode in="SourceGraphic"/>
          </feMerge>
        </filter>

        {/* Inner light */}
        <linearGradient id={`inner-light-${id}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="rgba(255,255,255,0.15)" />
          <stop offset="100%" stopColor="rgba(255,255,255,0.02)" />
        </linearGradient>
      </defs>

      {/* Node background with enhanced design */}
      <rect
        x={x - width / 2}
        y={y - height / 2}
        width={width}
        height={height}
        rx={8}
        fill={`url(#grad-${id})`}
        stroke={`url(#border-${id})`}
        strokeWidth={1.5}
        style={{
          cursor: onClick ? 'pointer' : 'default',
          transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
          filter:
            status === 'running'
              ? `drop-shadow(0 0 ${40 * shadowIntensity}px rgba(0, 229, 255, ${0.8 * shadowIntensity})) drop-shadow(0 0 ${80 * shadowIntensity}px rgba(0, 229, 255, ${0.4 * shadowIntensity})) drop-shadow(0 0 ${120 * shadowIntensity}px rgba(0, 229, 255, ${0.2 * shadowIntensity}))`
              : status === 'error'
              ? `drop-shadow(0 0 ${35 * shadowIntensity}px rgba(255, 90, 107, ${0.8 * shadowIntensity})) drop-shadow(0 0 ${70 * shadowIntensity}px rgba(255, 90, 107, ${0.4 * shadowIntensity}))`
              : status === 'success'
              ? `drop-shadow(0 0 ${30 * shadowIntensity}px rgba(20, 191, 138, ${0.7 * shadowIntensity})) drop-shadow(0 0 ${60 * shadowIntensity}px rgba(20, 191, 138, ${0.3 * shadowIntensity}))`
              : isHovering
              ? 'drop-shadow(0 0 30px rgba(0, 229, 255, 0.7)) drop-shadow(0 0 60px rgba(0, 229, 255, 0.35))'
              : enabled
              ? 'drop-shadow(0 0 20px rgba(0, 229, 255, 0.25)) drop-shadow(0 0 40px rgba(0, 229, 255, 0.12))'
              : 'drop-shadow(0 0 10px rgba(85, 102, 134, 0.2))'
        }}
        onClick={handleClick}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      />

      {/* Inner light overlay */}
      <rect
        x={x - width / 2 + 1}
        y={y - height / 2 + 1}
        width={width - 2}
        height={height - 2}
        rx={7}
        fill={`url(#inner-light-${id})`}
        opacity={enabled ? (isHovering ? 0.4 : 0.25) : 0.1}
        style={{
          transition: 'opacity 0.3s ease',
          pointerEvents: 'none'
        }}
      />

      {/* Surface details - corner highlights */}
      {enabled && (
        <>
          <line
            x1={x - width / 2 + 8}
            y1={y - height / 2 + 1}
            x2={x - width / 2 + 24}
            y2={y - height / 2 + 1}
            stroke="rgba(255,255,255,0.3)"
            strokeWidth={0.5}
            opacity={isHovering ? 0.6 : 0.3}
            style={{ transition: 'opacity 0.3s ease' }}
          />
          <line
            x1={x - width / 2 + 1}
            y1={y - height / 2 + 8}
            x2={x - width / 2 + 1}
            y2={y - height / 2 + 20}
            stroke="rgba(255,255,255,0.25)"
            strokeWidth={0.5}
            opacity={isHovering ? 0.5 : 0.25}
            style={{ transition: 'opacity 0.3s ease' }}
          />
        </>
      )}

      {/* Enhanced pulse effects for active states */}
      {status === 'running' && (
        <>
          <rect
            x={x - width / 2 - 2}
            y={y - height / 2 - 2}
            width={width + 4}
            height={height + 4}
            rx={10}
            fill="none"
            stroke={fillColor}
            strokeWidth={1.5}
            opacity={0.7}
            style={{
              animation: 'pulse-outer 2s infinite',
              animationDelay: '0s'
            }}
          />
          <rect
            x={x - width / 2 - 1}
            y={y - height / 2 - 1}
            width={width + 2}
            height={height + 2}
            rx={9}
            fill="none"
            stroke={fillColor}
            strokeWidth={1}
            opacity={0.8}
            style={{
              animation: 'pulse-inner 1.5s infinite',
              animationDelay: '0.3s'
            }}
          />
        </>
      )}

      {/* Breathing effect for idle nodes */}
      {status === 'idle' && enabled && (
        <rect
          x={x - width / 2}
          y={y - height / 2}
          width={width}
          height={height}
          rx={8}
          fill="none"
          stroke={fillColor}
          strokeWidth={0.8}
          opacity={0.4}
          style={{
            animation: 'breathe 4s infinite ease-in-out',
            animationDelay: getIdleAnimationDelay(id)
          }}
        />
      )}

      {/* Node text */}
      <text
        x={x}
        y={y + 5}
        textAnchor="middle"
        fill={textColor}
        fontSize="14"
        fontWeight="700"
        pointerEvents="none"
        style={{
          fontFamily: 'var(--font-heading)',
          letterSpacing: '0.04em',
          opacity: enabled ? 0.95 : 0.6
        }}
      >
        {label}
      </text>

      {/* Agent indicator */}
      {isAgent && (
        <circle
          cx={x + width / 2 - 8}
          cy={y - height / 2 + 8}
          r={3}
          fill={enabled ? 'var(--hud-accent)' : '#607299'}
          opacity={0.8}
        />
      )}

      <style jsx>{`
        @keyframes pulse-outer {
          0%, 100% {
            opacity: 0.3;
            transform: scale(1);
          }
          50% {
            opacity: 0.7;
            transform: scale(1.08);
          }
        }

        @keyframes pulse-inner {
          0%, 100% {
            opacity: 0.5;
            transform: scale(1);
          }
          50% {
            opacity: 0.8;
            transform: scale(1.04);
          }
        }

        @keyframes breathe {
          0%, 100% {
            opacity: 0.2;
            transform: scale(1);
          }
          50% {
            opacity: 0.4;
            transform: scale(1.015);
          }
        }
      `}</style>
    </g>
  );
}