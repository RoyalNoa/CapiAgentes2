'use client';

import React from 'react';
import { useViewportOptimization } from '@/app/hooks/useViewportOptimization';
import styles from './ViewportOptimizer.module.css';

export const ViewportOptimizer: React.FC = () => {
  const { viewportData, showZoomWarning, dismissWarning, resetZoom } = useViewportOptimization();

  if (!showZoomWarning) return null;

  return (
    <>
      {/* Overlay semi-transparente */}
      <div className={styles.overlay} onClick={dismissWarning} />

      {/* Panel de optimización */}
      <div className={styles.optimizerPanel}>
        <div className={styles.header}>
          <div className={styles.icon}>⚡</div>
          <h3>OPTIMIZACIÓN DE VIEWPORT</h3>
          <button className={styles.closeBtn} onClick={dismissWarning}>
            ×
          </button>
        </div>

        <div className={styles.content}>
          <div className={styles.warning}>
            <strong>Elementos fuera del viewport detectados</strong>
          </div>

          <div className={styles.metrics}>
            <div className={styles.metricItem}>
              <span className={styles.label}>Zoom estimado:</span>
              <span className={styles.value}>{Math.round(viewportData.zoom * 100)}%</span>
            </div>
            <div className={styles.metricItem}>
              <span className={styles.label}>Viewport:</span>
              <span className={styles.value}>
                {viewportData.viewportWidth}×{viewportData.viewportHeight}
              </span>
            </div>
          </div>

          <div className={styles.recommendation}>
            {viewportData.recommendation}
          </div>

          <div className={styles.actions}>
            <button className={styles.primaryBtn} onClick={resetZoom}>
              🎯 Configurar Zoom Óptimo
            </button>
            <button className={styles.secondaryBtn} onClick={dismissWarning}>
              ✓ Continuar Así
            </button>
          </div>

          <div className={styles.tips}>
            <div className={styles.tip}>
              <strong>Shortcuts útiles:</strong>
            </div>
            <div className={styles.shortcut}>
              <kbd>Ctrl</kbd> + <kbd>0</kbd> → Resetear zoom al 100%
            </div>
            <div className={styles.shortcut}>
              <kbd>Ctrl</kbd> + <kbd>-</kbd> → Reducir zoom
            </div>
            <div className={styles.shortcut}>
              <kbd>F11</kbd> → Pantalla completa
            </div>
          </div>
        </div>
      </div>
    </>
  );
};

export default ViewportOptimizer;