'use client';

import React from 'react';
import { useViewportOptimization } from '@/app/hooks/useViewportOptimization';
import styles from './ViewportIndicator.module.css';

export const ViewportIndicator: React.FC = () => {
  const { viewportData } = useViewportOptimization();

  const getStatusColor = () => {
    if (viewportData.isOptimal) return 'optimal';
    if (viewportData.viewportHeight < 500) return 'critical';
    if (viewportData.viewportHeight < 700) return 'warning';
    return 'info';
  };

  const getStatusIcon = () => {
    const status = getStatusColor();
    switch (status) {
      case 'optimal': return '✓';
      case 'critical': return '⚠';
      case 'warning': return '⚡';
      default: return 'ⓘ';
    }
  };

  return (
    <div className={`${styles.indicator} ${styles[getStatusColor()]}`} title={viewportData.recommendation}>
      <div className={styles.icon}>
        {getStatusIcon()}
      </div>
      <div className={styles.metrics}>
        <div className={styles.viewport}>
          {viewportData.viewportWidth}×{viewportData.viewportHeight}
        </div>
        <div className={styles.zoom}>
          {Math.round(viewportData.zoom * 100)}%
        </div>
      </div>
    </div>
  );
};

export default ViewportIndicator;