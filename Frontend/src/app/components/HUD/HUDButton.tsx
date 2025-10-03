/**
 * Ruta: Frontend/src/app/components/HUD/HUDButton.tsx
 * Descripción: Botón HUD reutilizable con variantes (primary, danger, ghost).
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 * Referencias: AI/estandares.md
 */
'use client';

import React from 'react';

type Variant = 'primary' | 'danger' | 'ghost';
type Size = 'sm' | 'md';

interface HUDButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export default function HUDButton({ variant = 'primary', size = 'md', className = '', children, ...rest }: HUDButtonProps) {
  const sizeClass = size === 'sm' ? 'px-2 py-1 text-xs' : 'px-4 py-2';
  const base = `${sizeClass} hud-btn`;
  const variantClass = variant === 'danger' ? 'danger' : variant === 'ghost' ? 'ghost' : 'primary';

  return (
    <button className={`${base} ${variantClass} ${className}`} {...rest}>
      {children}
    </button>
  );
}
