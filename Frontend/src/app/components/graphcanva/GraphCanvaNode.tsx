"use client";

import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";

import type { GraphCanvaNodeDataPayload } from "./types";
import styles from "./styles/graphCanva.module.css";

const STATUS_ICON: Record<string, string> = {
  idle: "⏺",
  running: "⏳",
  success: "✅",
  error: "⚠️",
  waiting: "🕒",
};

function GraphCanvaNodeComponent({ data, selected }: NodeProps<GraphCanvaNodeDataPayload>) {
  const icon = STATUS_ICON[data.status] ?? STATUS_ICON.idle;
  return (
    <div
      className={[
        styles.node,
        styles[`status-${data.status}`] ?? "",
        selected ? styles.selected : "",
        data.isDisabled ? styles.disabled : "",
      ].join(" ").trim()}
      data-testid="graphcanva-node"
    >
      <Handle type="target" position={Position.Left} className={styles.handleLeft} />
      <div className={styles.header}>
        <span className={styles.statusIcon} aria-hidden>
          {icon}
        </span>
        <div className={styles.titleGroup}>
          <span className={styles.title}>{data.label}</span>
          <span className={styles.subtitle}>{data.subtitle}</span>
        </div>
      </div>
      <div className={styles.body}>
        <dl className={styles.metricsList}>
          {data.metrics && "trigger_count" in data.metrics ? (
            <div>
              <dt>Triggers</dt>
              <dd>{String(data.metrics.trigger_count)}</dd>
            </div>
          ) : null}
          {data.lastRunAt ? (
            <div>
              <dt>Last run</dt>
              <dd>{new Date(data.lastRunAt).toLocaleString()}</dd>
            </div>
          ) : (
            <div>
              <dt>Status</dt>
              <dd>{data.status}</dd>
            </div>
          )}
        </dl>
      </div>
      <Handle type="source" position={Position.Right} className={styles.handleRight} />
    </div>
  );
}

export const GraphCanvaNode = memo(GraphCanvaNodeComponent);
