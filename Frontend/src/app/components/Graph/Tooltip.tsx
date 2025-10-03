/**
 * Ruta: Frontend/src/app/components/Graph/Tooltip.tsx
 * Descripción: Tooltip HUD para mostrar metadatos de nodos/edges con estética Ironman.
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 * Referencias: AI/estandares.md
 */
'use client';

import React, { useEffect, useState } from 'react';

interface TooltipProps {
  show: boolean;
  x: number;
  y: number;
  content: React.ReactNode;
  delay?: number;
  className?: string;
}

export default function Tooltip({
  show,
  x,
  y,
  content,
  delay = 120,
  className = ''
}: TooltipProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    if (show) {
      timeoutId = setTimeout(() => {
        setIsVisible(true);
      }, delay);
    } else {
      setIsVisible(false);
    }

    return () => {
      if (timeoutId) {
        clearTimeout(timeoutId);
      }
    };
  }, [show, delay]);

  if (!isVisible) {
    return null;
  }

  return (
    <div
      className={`absolute z-50 px-3 py-2 text-sm rounded-md shadow-lg max-w-xs hud-tooltip ${className}`}
      style={{
        left: x,
        top: y - 10,
        transform: 'translate(-50%, -100%)',
        pointerEvents: 'none'
      }}
    >
      {/* Tooltip arrow */}
      <div
        className="absolute top-full left-1/2 transform -translate-x-1/2"
        style={{
          width: 0,
          height: 0,
          borderLeft: '4px solid transparent',
          borderRight: '4px solid transparent',
          borderTop: '4px solid #14233c'
        }}
      />

      {/* Tooltip content */}
      <div className="text-center">
        {content}
      </div>
    </div>
  );
}