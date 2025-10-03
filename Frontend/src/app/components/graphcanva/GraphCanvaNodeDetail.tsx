"use client";

import { memo } from "react";

import styles from "./styles/graphCanva.module.css";

interface GraphCanvaNodeDetailProps {
  nodeName: string;
  payload: Record<string, unknown>;
  onClose: () => void;
}

function GraphCanvaNodeDetailComponent({ nodeName, payload, onClose }: GraphCanvaNodeDetailProps) {
  return (
    <aside className={styles.ndvPanel} role="dialog" aria-modal="true" aria-label={`Detalle de ${nodeName}`}>
      <header className={styles.ndvHeader}>
        <h4 className={styles.ndvTitle}>{nodeName}</h4>
        <button type="button" className={styles.ndvClose} onClick={onClose}>
          Cerrar
        </button>
      </header>
      <div className={styles.ndvBody}>
        <pre className={styles.ndvPre}>{JSON.stringify(payload, null, 2)}</pre>
      </div>
    </aside>
  );
}

export const GraphCanvaNodeDetail = memo(GraphCanvaNodeDetailComponent);
