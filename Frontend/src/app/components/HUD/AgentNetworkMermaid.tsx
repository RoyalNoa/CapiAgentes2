"use client";

import React, { useEffect, useRef, useState } from "react";
import mermaid from "mermaid";
import styles from "./GraphPanel.module.css";

interface AgentNetworkMermaidProps {
  variant: "svg" | "png" | "conceptual";
  diagram: string | null;
  diagramPng?: string | null;
  diagramPngMime?: string | null;
  diagramPngError?: string | null;
  loading: boolean;
  error: string | null;
  onRetry?: () => void;
}

const mermaidConfig = {
  startOnLoad: false,
  securityLevel: "loose",
  flowchart: {
    htmlLabels: false,
    useMaxWidth: false,
    padding: 24,
    nodeSpacing: 60,
    rankSpacing: 80,
  },
};

const AgentNetworkMermaid: React.FC<AgentNetworkMermaidProps> = ({
  variant,
  diagram,
  diagramPng,
  diagramPngMime,
  diagramPngError,
  loading,
  error,
  onRetry,
}) => {
  const viewportRef = useRef<HTMLDivElement | null>(null);
  const initializedRef = useRef(false);
  const [svgMarkup, setSvgMarkup] = useState<string | null>(null);
  const [renderError, setRenderError] = useState<string | null>(null);

  const hasPng = typeof diagramPng === "string" && diagramPng.length > 0;
  const pngSrc = hasPng ? `data:${diagramPngMime || "image/png"};base64,${diagramPng}` : null;
  const isPngVariant = variant === "png";

  useEffect(() => {
    if (!initializedRef.current) {
      mermaid.initialize(mermaidConfig);
      initializedRef.current = true;
    }
  }, []);

  useEffect(() => {
    if (isPngVariant) {
      setSvgMarkup(null);
      setRenderError(null);
      return;
    }

    if (!diagram || loading || error) {
      setSvgMarkup(null);
      setRenderError(null);
      return;
    }

    let cancelled = false;
    const renderId = `agent-network-${Math.random().toString(36).slice(2)}`;

    const renderDiagram = async () => {
      try {
        setRenderError(null);
        const { svg } = await mermaid.render(renderId, diagram);
        if (!cancelled) {
          setSvgMarkup(svg);
        }
      } catch (err) {
        if (cancelled) {
          return;
        }
        const message = err instanceof Error ? err.message : String(err);
        setRenderError(message);
        setSvgMarkup(null);
      }
    };

    renderDiagram();

    return () => {
      cancelled = true;
    };
  }, [diagram, loading, error, isPngVariant]);

  useEffect(() => {
    if (!svgMarkup || isPngVariant) {
      return;
    }

    const container = viewportRef.current;
    const svgElement = container?.querySelector("svg");
    if (!svgElement) {
      return;
    }

    svgElement.removeAttribute("width");
    svgElement.removeAttribute("height");
    svgElement.style.width = "100%";
    svgElement.style.height = "auto";
    svgElement.style.maxWidth = "none";
    svgElement.setAttribute("preserveAspectRatio", "xMinYMin meet");
  }, [svgMarkup, isPngVariant]);

  return (
    <div className={styles.mermaidViewportShell}>
      <div ref={viewportRef} className={styles.mermaidViewport}>
        {isPngVariant ? (
          hasPng && pngSrc ? (
            <img src={pngSrc} alt="Diagrama de agentes en PNG" className={styles.mermaidPngImage} />
          ) : !loading ? (
            <div className={styles.mermaidPlaceholder}>PNG no disponible</div>
          ) : null
        ) : svgMarkup ? (
          <div className={styles.mermaidSvgHost} dangerouslySetInnerHTML={{ __html: svgMarkup }} />
        ) : !diagram && !loading && !error ? (
          <div className={styles.mermaidPlaceholder}>Sin diagrama disponible</div>
        ) : null}
      </div>

      {loading ? <div className={styles.mermaidStatus}>Cargando diagrama mermaid...</div> : null}

      {error ? (
        <div className={styles.mermaidStatus}>
          <span>Error al cargar diagrama: {error}</span>
          {onRetry ? (
            <button type="button" className={styles.mermaidRetry} onClick={onRetry}>
              Reintentar
            </button>
          ) : null}
        </div>
      ) : null}

      {!isPngVariant && renderError ? (
        <div className={styles.mermaidStatus}>Error al renderizar Mermaid: {renderError}</div>
      ) : null}

      {isPngVariant && diagramPngError ? (
        <div className={styles.mermaidStatus}>Error al renderizar PNG: {diagramPngError}</div>
      ) : null}
    </div>
  );
};

export default AgentNetworkMermaid;
