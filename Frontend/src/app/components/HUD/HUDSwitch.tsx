/**
 * Ruta: Frontend/src/app/components/HUD/HUDSwitch.tsx
 * Descripción: Interruptor HUD reutilizable (toggle) con estética Ironman HUD.
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 */

'use client';

import React from 'react';

type Size = 'sm' | 'md';

export interface HUDSwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  id?: string;
  label?: React.ReactNode;
  size?: Size;
  className?: string;
}

const sizeMap: Record<Size, { track: { w: number; h: number }; thumb: { size: number; translate: number } }> = {
  sm: { track: { w: 40, h: 22 }, thumb: { size: 18, translate: 18 } },
  md: { track: { w: 44, h: 24 }, thumb: { size: 20, translate: 20 } },
};

export default function HUDSwitch({ checked, onChange, disabled, id, label, size = 'md', className = '' }: HUDSwitchProps) {
  const s = sizeMap[size];
  const generatedId = React.useId();
  const inputId = id ?? generatedId;

  return (
    <label htmlFor={inputId} className={`hud-switch ${size} ${disabled ? 'is-disabled' : ''} ${className}`.trim()}>
      <input
        id={inputId}
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        disabled={disabled}
      />
      <span
        className="track"
        style={{ width: s.track.w, height: s.track.h }}
        aria-hidden
      >
        <span
          className="thumb"
          style={{ width: s.thumb.size, height: s.thumb.size, transform: checked ? `translateX(${s.thumb.translate}px)` : 'translateX(0)' }}
        />
      </span>
      {label ? <span className="label hud-small">{label}</span> : null}
    </label>
  );
}


