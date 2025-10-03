"use client";

import React, { useCallback, useEffect, useState } from "react";
import AgentNetworkMermaid from "./AgentNetworkMermaid";
import { GraphCanvaOverview } from "@/app/components/graphcanva";
import type { CapiNoticiasSegmentControls } from "./CapiNoticiasSegmentCard";
import styles from "./GraphPanel.module.css";
import {
  getLangGraphMermaidSvg,
  getLangGraphMermaidPng,
  getLangGraphMermaidConceptual,
} from "@/app/utils/orchestrator/client";

interface AgentMetrics {
  tokens_used?: number;
  cost_usd?: number;
  requests?: number;
  avg_response_time?: number;
}

interface AgentData {
  name: string;
  enabled: boolean;
  description: string;
  status: string;
  metrics?: AgentMetrics;
}

interface SystemStatusDto {
  active_agents: number;
  total_agents: number;
  system_operational?: boolean;
  timestamp?: string;
}

interface Event {
  id: string;
  type: string;
  timestamp: string;
  data?: Record<string, unknown>;
}

interface LiveWorkflowState {
  sessionId: string | null;
  currentNode?: string | null;
  previousNode?: string | null;
  completedNodes?: string[];
  status?: string;
  step?: number | null;
  snapshot?: Record<string, unknown> | null;
}

interface GraphPanelProps {
  agents: AgentData[];
  systemStatus: SystemStatusDto | null;
  isConnected: boolean;
  selectedAgent: string | null;
  onSelectAgent: (agentName: string | null) => void;
  events: Event[];
  onAgentsUpdate: () => void;
  liveFlow?: LiveWorkflowState | null;
  capiNoticiasControls?: CapiNoticiasSegmentControls;
}

const VIEW_MODES = {
  overview: "overview",
  mermaid: "mermaid",
} as const;

type ViewMode = (typeof VIEW_MODES)[keyof typeof VIEW_MODES];

const GRAPH_VARIANTS = {
  svg: "svg",
  png: "png",
  conceptual: "conceptual",
} as const;

type GraphVariant = (typeof GRAPH_VARIANTS)[keyof typeof GRAPH_VARIANTS];

const connectionLabel = (isConnected: boolean) => (isConnected ? "Connected" : "Disconnected");

const GraphPanel: React.FC<GraphPanelProps> = ({
  agents,
  systemStatus,
  isConnected,
  selectedAgent,
  onSelectAgent,
  events,
  onAgentsUpdate,
  liveFlow,
  capiNoticiasControls,
}) => {
  void agents;
  void systemStatus;
  void selectedAgent;
  void onSelectAgent;
  void events;
  void onAgentsUpdate;
  void liveFlow;
  void capiNoticiasControls;

  const [viewMode, setViewMode] = useState<ViewMode>(VIEW_MODES.overview);
  const [graphVariant, setGraphVariant] = useState<GraphVariant>(GRAPH_VARIANTS.svg);

  const [mermaidSvg, setMermaidSvg] = useState<string | null>(null);
  const [mermaidSvgLoading, setMermaidSvgLoading] = useState(false);
  const [mermaidSvgError, setMermaidSvgError] = useState<string | null>(null);

  const [mermaidPng, setMermaidPng] = useState<string | null>(null);
  const [mermaidPngMime, setMermaidPngMime] = useState<string | null>(null);
  const [mermaidPngError, setMermaidPngError] = useState<string | null>(null);
  const [mermaidPngLoading, setMermaidPngLoading] = useState(false);

  const [mermaidConceptual, setMermaidConceptual] = useState<string | null>(null);
  const [mermaidConceptualLoading, setMermaidConceptualLoading] = useState(false);
  const [mermaidConceptualError, setMermaidConceptualError] = useState<string | null>(null);

  const fetchMermaidSvg = useCallback(async () => {
    setMermaidSvgLoading(true);
    setMermaidSvgError(null);
    try {
      const payload = await getLangGraphMermaidSvg();
      const diagramSource = typeof payload?.diagram === "string" ? payload.diagram : null;
      setMermaidSvg(diagramSource);
      setMermaidSvgError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setMermaidSvgError(message);
      setMermaidSvg(null);
    } finally {
      setMermaidSvgLoading(false);
    }
  }, []);

  const fetchMermaidPng = useCallback(async () => {
    setMermaidPngLoading(true);
    setMermaidPngError(null);
    try {
      const payload = await getLangGraphMermaidPng();
      const pngSource = typeof payload?.diagram_png === "string" && payload.diagram_png.length > 0 ? payload.diagram_png : null;
      const pngError = typeof payload?.diagram_png_error === "string" ? payload.diagram_png_error : null;
      const pngMime = typeof payload?.diagram_png_mime === "string" && payload.diagram_png_mime ? payload.diagram_png_mime : null;

      setMermaidPng(pngSource);
      setMermaidPngMime(pngSource ? pngMime || "image/png" : null);
      setMermaidPngError(pngSource ? null : pngError);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setMermaidPng(null);
      setMermaidPngMime(null);
      setMermaidPngError(message);
    } finally {
      setMermaidPngLoading(false);
    }
  }, []);

  const fetchMermaidConceptual = useCallback(async () => {
    setMermaidConceptualLoading(true);
    setMermaidConceptualError(null);
    try {
      const payload = await getLangGraphMermaidConceptual();
      const diagramSource = typeof payload?.diagram === "string" ? payload.diagram : null;
      setMermaidConceptual(diagramSource);
      setMermaidConceptualError(null);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setMermaidConceptualError(message);
      setMermaidConceptual(null);
    } finally {
      setMermaidConceptualLoading(false);
    }
  }, []);

  useEffect(() => {
    void fetchMermaidSvg();
  }, [fetchMermaidSvg]);

  useEffect(() => {
    if (viewMode !== VIEW_MODES.mermaid) {
      return;
    }

    if (graphVariant === GRAPH_VARIANTS.svg && !mermaidSvg && !mermaidSvgLoading && !mermaidSvgError) {
      void fetchMermaidSvg();
      return;
    }

    if (graphVariant === GRAPH_VARIANTS.png && !mermaidPng && !mermaidPngLoading && !mermaidPngError) {
      void fetchMermaidPng();
      return;
    }

    if (
      graphVariant === GRAPH_VARIANTS.conceptual &&
      !mermaidConceptual &&
      !mermaidConceptualLoading &&
      !mermaidConceptualError
    ) {
      void fetchMermaidConceptual();
    }
  }, [
    viewMode,
    graphVariant,
    mermaidSvg,
    mermaidSvgLoading,
    mermaidSvgError,
    mermaidPng,
    mermaidPngLoading,
    mermaidPngError,
    mermaidConceptual,
    mermaidConceptualLoading,
    mermaidConceptualError,
    fetchMermaidSvg,
    fetchMermaidPng,
    fetchMermaidConceptual,
  ]);

  const handleVariantChange = useCallback(
    (variant: GraphVariant) => {
      setGraphVariant(variant);

      if (variant === GRAPH_VARIANTS.png && !mermaidPng && !mermaidPngLoading) {
        void fetchMermaidPng();
      }

      if (variant === GRAPH_VARIANTS.conceptual && !mermaidConceptual && !mermaidConceptualLoading) {
        void fetchMermaidConceptual();
      }
    },
    [
      fetchMermaidPng,
      fetchMermaidConceptual,
      mermaidPng,
      mermaidPngLoading,
      mermaidConceptual,
      mermaidConceptualLoading,
    ],
  );

  const handleRetry = useCallback(() => {
    if (graphVariant === GRAPH_VARIANTS.svg) {
      void fetchMermaidSvg();
      return;
    }

    if (graphVariant === GRAPH_VARIANTS.png) {
      void fetchMermaidPng();
      return;
    }

    void fetchMermaidConceptual();
  }, [graphVariant, fetchMermaidSvg, fetchMermaidPng, fetchMermaidConceptual]);

  const activeLoading =
    graphVariant === GRAPH_VARIANTS.svg
      ? mermaidSvgLoading
      : graphVariant === GRAPH_VARIANTS.png
        ? mermaidPngLoading
        : mermaidConceptualLoading;

  const activeError =
    graphVariant === GRAPH_VARIANTS.svg
      ? mermaidSvgError
      : graphVariant === GRAPH_VARIANTS.png
        ? mermaidPngError
        : mermaidConceptualError;

  const activeDiagram =
    graphVariant === GRAPH_VARIANTS.conceptual ? mermaidConceptual : mermaidSvg;
  const panelTitle = viewMode === VIEW_MODES.overview ? 'Agent Workflow' : 'Agent Network';

  return (
    <section className={styles.panel}>
      <header className={styles.header}>
        <div className={styles.titleGroup}>
          <h2 className={styles.title}>{panelTitle}</h2>
          <span
            className={`${styles.connectionBadge} ${isConnected ? styles.connectionOnline : styles.connectionOffline}`}
            aria-live="polite"
          >
            {connectionLabel(isConnected)}
          </span>
        </div>
        <div className={styles.toggleGroup} role="group" aria-label="Agent network view mode">
          <button
            type="button"
            className={`${styles.toggleButton} ${viewMode === VIEW_MODES.overview ? styles.toggleButtonActive : ""}`}
            onClick={() => setViewMode(VIEW_MODES.overview)}
            aria-pressed={viewMode === VIEW_MODES.overview}
          >
            Overview
          </button>
          <button
            type="button"
            className={`${styles.toggleButton} ${viewMode === VIEW_MODES.mermaid ? styles.toggleButtonActive : ""}`}
            onClick={() => setViewMode(VIEW_MODES.mermaid)}
            aria-pressed={viewMode === VIEW_MODES.mermaid}
          >
            Mermaid
          </button>
        </div>
      </header>

      <div className={styles.body}>
        {viewMode === VIEW_MODES.overview ? (
          <div className={styles.overviewSurface}>
            <GraphCanvaOverview workflowId="graph-canva-demo" />
          </div>
        ) : (
          <div className={styles.mermaidSurface}>
            <div className={styles.graphVariantSwitch} role="group" aria-label="Representación del grafo">
              <button
                type="button"
                className={`${styles.graphVariantButton} ${graphVariant === GRAPH_VARIANTS.svg ? styles.graphVariantButtonActive : ""}`.trim()}
                onClick={() => handleVariantChange(GRAPH_VARIANTS.svg)}
                aria-pressed={graphVariant === GRAPH_VARIANTS.svg}
                disabled={graphVariant === GRAPH_VARIANTS.svg && mermaidSvgLoading}
              >
                SVG
              </button>
              <button
                type="button"
                className={`${styles.graphVariantButton} ${graphVariant === GRAPH_VARIANTS.png ? styles.graphVariantButtonActive : ""}`.trim()}
                onClick={() => handleVariantChange(GRAPH_VARIANTS.png)}
                aria-pressed={graphVariant === GRAPH_VARIANTS.png}
                disabled={graphVariant === GRAPH_VARIANTS.png && mermaidPngLoading}
              >
                PNG
              </button>
              <button
                type="button"
                className={`${styles.graphVariantButton} ${graphVariant === GRAPH_VARIANTS.conceptual ? styles.graphVariantButtonActive : ""}`.trim()}
                onClick={() => handleVariantChange(GRAPH_VARIANTS.conceptual)}
                aria-pressed={graphVariant === GRAPH_VARIANTS.conceptual}
                disabled={graphVariant === GRAPH_VARIANTS.conceptual && mermaidConceptualLoading}
              >
                CPT
              </button>
            </div>
            <AgentNetworkMermaid
              variant={graphVariant}
              diagram={activeDiagram}
              diagramPng={mermaidPng}
              diagramPngMime={mermaidPngMime}
              diagramPngError={mermaidPngError}
              loading={activeLoading}
              error={activeError}
              onRetry={handleRetry}
            />
          </div>
        )}
      </div>
    </section>
  );
};

export default GraphPanel;
