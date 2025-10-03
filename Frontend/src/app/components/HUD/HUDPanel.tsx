/**
 * Ruta: Frontend/src/app/components/HUD/HUDPanel.tsx
 * Descripción: Panel reutilizable con estética HUD/Glass para secciones de la UI.
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 * Referencias: AI/estandares.md
 */
'use client';

import React from 'react';

interface HUDPanelProps {
  title?: React.ReactNode;
  headerRight?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  contentClassName?: string;
}

export default function HUDPanel({ title, headerRight, children, className = '', contentClassName = '' }: HUDPanelProps) {
  return (
    <div className={`hud-panel rounded-lg ${className}`}>
      {(title || headerRight) && (
        <div className="p-4 border-b border-gray-800/60 flex items-center justify-between">
          {typeof title === 'string' ? <h3 className="text-lg hud-title">{title}</h3> : title}
          {headerRight}
        </div>
      )}
      <div className={`p-4 ${contentClassName}`}>{children}</div>
    </div>
  );
}
