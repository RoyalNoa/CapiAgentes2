/**
 * Ruta: Frontend/src/app/components/HUD/HUDBadge.tsx
 * Descripción: Badge/Chip con variantes HUD para estados o métricas.
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 * Referencias: AI/estandares.md
 */
'use client';

import React from 'react';

type Variant = 'live' | 'warn' | 'idle' | 'ok' | 'error' | 'neutral';

interface HUDBadgeProps {
  children: React.ReactNode;
  variant?: Variant;
  className?: string;
}

export default function HUDBadge({ children, variant = 'neutral', className = '' }: HUDBadgeProps) {
  const variantClass =
    variant === 'live' ? 'hud-badge live' :
    variant === 'warn' ? 'hud-badge warn' :
    'hud-badge';

  return (
    <span className={`px-3 py-1 rounded ${variantClass} ${className}`}>{children}</span>
  );
}
