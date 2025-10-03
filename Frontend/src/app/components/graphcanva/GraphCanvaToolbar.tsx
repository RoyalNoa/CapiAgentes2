"use client";

import { memo } from "react";

import styles from "./styles/graphCanva.module.css";

type ConnectionStatus = "connected" | "connecting" | "disconnected";

interface GraphCanvaToolbarProps {
  onRun: () => void;
  onFitView: () => void;
  onResetViewport: () => void;
  disabled?: boolean;
  isRunning?: boolean;
  connectionStatus?: ConnectionStatus;
}

const statusLabel = {
  connected: "En vivo",
  connecting: "Conectando…",
  disconnected: "Sin conexión",
};

function GraphCanvaToolbarComponent({
  onRun,
  onFitView,
  onResetViewport,
  disabled = false,
  isRunning = false,
  connectionStatus = "connecting",
}: GraphCanvaToolbarProps) {
  return (
    <div className={styles.toolbar} role="toolbar" aria-label="GraphCanva toolbar">
      <div className={styles.toolbarLeftGroup}>
        <button
          type="button"
          className={styles.toolbarButton}
          onClick={onRun}
          disabled={disabled}
        >
          {isRunning ? "Ejecutando…" : "Ejecutar"}
        </button>
        <button type="button" className={styles.toolbarButton} onClick={onFitView}>
          Ajustar vista
        </button>
        <button type="button" className={styles.toolbarButton} onClick={onResetViewport}>
          Resetear viewport
        </button>
      </div>
      <div className={styles.toolbarStatus} data-status={connectionStatus}>
        <span className={styles.toolbarStatusDot} aria-hidden />
        <span>{statusLabel[connectionStatus]}</span>
      </div>
    </div>
  );
}

export const GraphCanvaToolbar = memo(GraphCanvaToolbarComponent);
