/*
CAPI - Grid Background Component
===============================
Ruta: /Frontend/src/app/components/Graph/GridBackground.tsx
Descripción: Componente de fondo de cuadrícula tipo n8n para visualización
de grafos. Renderiza grid SVG sutil para contexto visual en PantallaAgentes.
Estado: ✅ EN USO ACTIVO - Componente Graph de PantallaAgentes
Dependencias: React, SVG
Características: Grid configurable, dots/lines, colores personalizables
Propósito: Fondo visual para grafo de agentes estilo n8n
*/

'use client';

import React from 'react';

interface GridBackgroundProps {
  gridSize?: number;
  dotSize?: number;
  dotColor?: string;
  lineColor?: string;
  className?: string;
}

export default function GridBackground({
  gridSize = 20,
  dotSize = 1,
  dotColor = '#374151',
  lineColor = '#1f2937',
  className = ''
}: GridBackgroundProps) {
  const patternId = 'grid-pattern';
  const dotPatternId = 'dot-pattern';

  return (
    <div className={`absolute inset-0 ${className}`} style={{ zIndex: 0 }}>
      <svg
        className="w-full h-full"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Grid lines pattern */}
          <pattern
            id={patternId}
            width={gridSize}
            height={gridSize}
            patternUnits="userSpaceOnUse"
          >
            <path
              d={`M ${gridSize} 0 L 0 0 0 ${gridSize}`}
              fill="none"
              stroke={lineColor}
              strokeWidth="0.5"
              opacity="0.3"
            />
          </pattern>

          {/* Dot pattern overlay */}
          <pattern
            id={dotPatternId}
            width={gridSize * 4}
            height={gridSize * 4}
            patternUnits="userSpaceOnUse"
          >
            <circle
              cx={gridSize * 2}
              cy={gridSize * 2}
              r={dotSize}
              fill={dotColor}
              opacity="0.6"
            />
          </pattern>
        </defs>

        {/* Render grid lines */}
        <rect
          width="100%"
          height="100%"
          fill={`url(#${patternId})`}
        />

        {/* Render dots */}
        <rect
          width="100%"
          height="100%"
          fill={`url(#${dotPatternId})`}
        />
      </svg>
    </div>
  );
}