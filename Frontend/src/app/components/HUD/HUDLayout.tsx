/**
 * Ruta: Frontend/src/app/components/HUD/HUDLayout.tsx
 * Descripción: Componente de layout HUD futurista para la pantalla de agentes
 * Estado: Activo
 * Autor: Claude Code
 * Última actualización: 2025-09-14
 * Referencias: AI/Tablero/PantallaAgentes/Ejemplo esperado.png
 */

'use client';

import React from 'react';
import styles from './HUDLayout.module.css';
// Removed ViewportOptimizer and ViewportIndicator - redundant after architecture fixes

interface HUDLayoutProps {
  title: string;
  isConnected: boolean;
  onConnect: () => void;
  onDisconnect: () => void;
  leftPanel: React.ReactNode;
  centerPanel: React.ReactNode;
  rightPanel: React.ReactNode;
  statusBar?: React.ReactNode;
  children?: React.ReactNode;
}

export const HUDLayout: React.FC<HUDLayoutProps> = ({
  title: _title,
  isConnected: _isConnected,
  onConnect: _onConnect,
  onDisconnect: _onDisconnect,
  leftPanel,
  centerPanel,
  rightPanel,
  statusBar,
  children
}) => {
  return (
    <div className={styles.hudContainer}>
      {/* Scanline Effect */}
      <div className={styles.scanline} />

      {/* Decorative Elements */}
      <div className={styles.decorativeFrame}>
        <div className={styles.topFrame} />
        <div className={styles.bottomFrame} />
      </div>

      {/* Corner Elements */}
      <div className={styles.corners}>
        <div className={`${styles.corner} ${styles.topLeft}`} />
        <div className={`${styles.corner} ${styles.topRight}`} />
        <div className={`${styles.corner} ${styles.bottomLeft}`} />
        <div className={`${styles.corner} ${styles.bottomRight}`} />
      </div>

      {/* Main Layout */}
      <div className={styles.mainLayout}>
        {/* Content Grid */}
        <main className={styles.contentGrid}>
          {/* Left Panel */}
          <section className={`${styles.panel} ${styles.leftPanel}`}>
            <div className={styles.panelContent}>
              {leftPanel}
            </div>
          </section>

          {/* Center Panel */}
          <section className={`${styles.panel} ${styles.centerPanel}`}>
            <div className={styles.panelContent}>
              {centerPanel}
            </div>
          </section>

          {/* Right Panel */}
          <section className={`${styles.panel} ${styles.rightPanel}`}>
            <div className={styles.panelContent}>
              {rightPanel}
            </div>
          </section>
        </main>

        {/* Status Bar */}
        {statusBar ? (
          <footer className={styles.statusBar}>
            {statusBar}
          </footer>
        ) : null}
      </div>

      {/* Additional Children */}
      {children}
    </div>
  );
};

export default HUDLayout;
