"use client";

import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from "react";
import { ArrowPathIcon } from "@heroicons/react/24/outline";
import { useHistoricalAlerts } from "@/app/contexts/HistoricalAlertsContext";
import {
  command,
  getHistoricalAlertDetail,
  updateAlertStatus,
  type HistoricalAlertDetailDto,
  type HistoricalAlertDeviceInfo,
  type HistoricalAlertSummaryDto,
  type HumanGateStatus,
  type AlertStatusUpdateRequest
} from "@/app/utils/orchestrator/client";
import styles from "./HistoricalAlertsDashboard.module.css";

interface HistoricalAlertsDashboardProps {
  isOpen: boolean;
  onClose: () => void;
  onShareWithAI?: (alertId: string, context: any) => void;
}

interface AlertDetailState {
  data?: HistoricalAlertDetailDto;
  loading: boolean;
  error?: string;
}

interface EnrichedAlert extends HistoricalAlertSummaryDto {
  humanStatus: HumanGateStatus;
  normalizedPriority: "critical" | "high" | "medium" | "low";
  priorityColor: string;
}

const STATUS_LABELS: Record<HumanGateStatus, string> = {
  pending: "Pendiente",
  accepted: "Aceptada",
  rejected: "Rechazada"
};

const PRIORITY_COLORS: Record<"critical" | "high" | "medium" | "low", string> = {
  critical: "#ff5b6b",
  high: "#ff9f43",
  medium: "#00b8ff",
  low: "#12d48a"
};

const DOCK_THRESHOLD = 80;
const MIN_DOCK_WIDTH = 320;
const MAX_DOCK_WIDTH = 520;
const FLOATING_WIDTH = 360;
const FLOATING_HEIGHT = 460;

const DETAIL_WINDOW_WIDTH = 420;
const DETAIL_WINDOW_HEIGHT = 540;

function normalizeInput(value?: string | null): string {
  return (value ?? "")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[^a-z0-9\s]/g, "");
}

function normalizePriority(priority?: string | null): "critical" | "high" | "medium" | "low" {
  const normalized = normalizeInput(priority);
  if (normalized.includes("crit")) return "critical";
  if (normalized.includes("alta") || normalized.includes("high")) return "high";
  if (normalized.includes("media") || normalized.includes("medium")) return "medium";
  return "low";
}

function normalizeStatus(status?: string | null): HumanGateStatus {
  const normalized = normalizeInput(status);
  if (normalized.includes("rechaz") || normalized.includes("silenc") || normalized.includes("reject")) {
    return "rejected";
  }
  if (
    normalized.includes("resuelt") ||
    normalized.includes("acept") ||
    normalized.includes("approved") ||
    normalized.includes("progres")
  ) {
    return "accepted";
  }
  return "pending";
}

function formatTimestamp(timestamp?: string | number): string {
  if (!timestamp) {
    return "Sin fecha";
  }
  const date = typeof timestamp === "number" ? new Date(timestamp) : new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return "Sin fecha";
  }
  return date.toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

function formatCurrencyValue(value?: number | null): string {
  if (value === null || value === undefined) {
    return 'N/D';
  }
  return new Intl.NumberFormat('es-AR', { style: 'currency', currency: 'ARS', maximumFractionDigits: 0 }).format(value);
}

function formatPercentValue(value?: number | null): string {
  if (value === null || value === undefined) {
    return 'N/D';
  }
  return `${value.toFixed(1)}%`;
}



function buildAlertPreview(alert: HistoricalAlertSummaryDto, detail?: HistoricalAlertDetailDto): string {
  if (detail?.description) {
    return detail.description;
  }
  const entities = Array.isArray(alert.affected_entities) ? alert.affected_entities : [];
  if (entities.length > 0) {
    return entities
      .map(entity => entity.entity_name || entity.entity_type)
      .filter(Boolean)
      .slice(0, 2)
      .join(" - ");
  }
  if (detail?.acciones) {
    return detail.acciones;
  }
  return "Sin descripcion disponible";
}

function buildDesktopPrompt(
  summary: HistoricalAlertSummaryDto,
  detail?: HistoricalAlertDetailDto
): string {
  const lines: string[] = [
    "HUMAN_GATE_APPROVED",
    `Alert ID: ${summary.id}`,
    `Code: ${detail?.alert_code ?? summary.alert_code ?? "N/D"}`,
    `Title: ${summary.title}`,
    `Priority: ${summary.priority}`,
    `Status: ${detail?.status ?? summary.status}`,
    `Timestamp: ${formatTimestamp(summary.timestamp)}`
  ];

  if (detail?.description) {
    lines.push(`Hipotesis: ${detail.description}`);
  }
  if (detail?.risk_assessment) {
    lines.push(`Impacto: ${detail.risk_assessment}`);
  }

  const dataPoints = detail?.datos_clave ?? [];
  if (dataPoints.length > 0) {
    lines.push("Datos clave:");
    dataPoints.forEach(point => lines.push(`- ${point}`));
  }

  if (detail?.acciones) {
    lines.push(`Accion sugerida: ${detail.acciones}`);
  }

  lines.push(
    "Accion requerida: Invocar al agente capi_desktop y preparar la evidencia en el escritorio del operador."
  );

  return lines.join("\n");
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

export default function HistoricalAlertsDashboard({
  isOpen,
  onClose,
  onShareWithAI
}: HistoricalAlertsDashboardProps) {
  const {
    alerts,
    loading,
    error,
    loadHistoricalData
  } = useHistoricalAlerts();

  const [activeAlertId, setActiveAlertId] = useState<string | null>(null);
  const [detailsById, setDetailsById] = useState<Record<string, AlertDetailState>>({});
  const [localStatuses, setLocalStatuses] = useState<Record<string, HumanGateStatus>>({});
  const [updatingAlertId, setUpdatingAlertId] = useState<string | null>(null);

  const [isResizing, setIsResizing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [isDocked, setIsDocked] = useState(true);
  const [dockedSide, setDockedSide] = useState<"left" | "right">("right");
  const [panelWidth, setPanelWidth] = useState(360);
  const [floatingPosition, setFloatingPosition] = useState({ x: 80, y: 120 });

  const [detailWindowAlertId, setDetailWindowAlertId] = useState<string | null>(null);
  const [detailWindowPosition, setDetailWindowPosition] = useState({ x: 420, y: 160 });
  const [isDetailDragging, setIsDetailDragging] = useState(false);
  const detailWindowDragRef = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null);

  const overlayRef = useRef<HTMLDivElement>(null);
  const dragStartRef = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null);

  useEffect(() => {
    if (!isOpen) {
      setDetailWindowAlertId(null);
      return;
    }
    setIsDocked(true);
    setDockedSide("left");
    setPanelWidth(360);
  }, [isOpen]);

  const fetchDetail = useCallback(async (alertId: string) => {
    setDetailsById(prev => ({
      ...prev,
      [alertId]: {
        data: prev[alertId]?.data,
        loading: true,
        error: undefined
      }
    }));

    try {
      const detail = await getHistoricalAlertDetail(alertId);
      setDetailsById(prev => ({
        ...prev,
        [alertId]: {
          data: detail,
          loading: false,
          error: undefined
        }
      }));
      return detail;
    } catch (err: any) {
      const message = err?.message ?? "No se pudo cargar el detalle";
      setDetailsById(prev => ({
        ...prev,
        [alertId]: {
          data: prev[alertId]?.data,
          loading: false,
          error: message
        }
      }));
      throw err;
    }
  }, []);

  const ensureDetail = useCallback(async (alertId: string) => {
    const existing = detailsById[alertId];
    if (existing?.data) {
      return existing.data;
    }
    try {
      return await fetchDetail(alertId);
    } catch {
      return undefined;
    }
  }, [detailsById, fetchDetail]);

  const enrichedAlerts: EnrichedAlert[] = useMemo(
    () =>
      alerts.map(alert => {
        const normalizedPriority = normalizePriority(alert.priority);
        const overrideStatus = localStatuses[alert.id];
        const humanStatus = overrideStatus ?? normalizeStatus(alert.status);

        return {
          ...alert,
          humanStatus,
          normalizedPriority,
          priorityColor: PRIORITY_COLORS[normalizedPriority]
        };
      }),
    [alerts, localStatuses]
  );

  useEffect(() => {
    if (!alerts.length) {
      setActiveAlertId(null);
      return;
    }
    setActiveAlertId(prev => {
      if (prev && alerts.some(alert => alert.id === prev)) {
        return prev;
      }
      return alerts[0].id;
    });
  }, [alerts]);

  useEffect(() => {
    if (!isOpen || !activeAlertId) {
      return;
    }
    const current = detailsById[activeAlertId];
    if (!current || (!current.data && !current.loading)) {
      void fetchDetail(activeAlertId);
    }
  }, [isOpen, activeAlertId, detailsById, fetchDetail]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    const handleMouseMove = (event: MouseEvent) => {
      if (isResizing) {
        const viewportWidth = window.innerWidth;
        let newWidth = dockedSide === "right" ? viewportWidth - event.clientX : event.clientX;
        newWidth = clamp(newWidth, MIN_DOCK_WIDTH, Math.min(MAX_DOCK_WIDTH, viewportWidth - 40));
        setPanelWidth(newWidth);
      }

      if (isDragging && dragStartRef.current) {
        const { x, y, startX, startY } = dragStartRef.current;
        const deltaX = event.clientX - x;
        const deltaY = event.clientY - y;

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        const referenceWidth = isDocked ? panelWidth : FLOATING_WIDTH;
        const newX = startX + deltaX;
        const newY = startY + deltaY;

        if (newX < DOCK_THRESHOLD) {
          setIsDocked(true);
          setDockedSide("left");
          setFloatingPosition({ x: 0, y: 0 });
          return;
        }
        if (newX + referenceWidth > viewportWidth - DOCK_THRESHOLD) {
          setIsDocked(true);
          setDockedSide("right");
          setFloatingPosition({ x: viewportWidth - FLOATING_WIDTH, y: 0 });
          return;
        }

        const maxX = Math.max(16, viewportWidth - FLOATING_WIDTH - 16);
        const maxY = Math.max(16, viewportHeight - FLOATING_HEIGHT - 16);
        setIsDocked(false);
        setFloatingPosition({
          x: clamp(newX, 16, maxX),
          y: clamp(newY, 16, maxY)
        });
      }

      if (isDetailDragging && detailWindowDragRef.current) {
        const { x, y, startX, startY } = detailWindowDragRef.current;
        const deltaX = event.clientX - x;
        const deltaY = event.clientY - y;

        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;

        const newX = clamp(startX + deltaX, 16, Math.max(16, viewportWidth - DETAIL_WINDOW_WIDTH - 16));
        const newY = clamp(startY + deltaY, 16, Math.max(16, viewportHeight - DETAIL_WINDOW_HEIGHT - 16));
        setDetailWindowPosition({ x: newX, y: newY });
      }
    };

    const handleMouseUp = () => {
      setIsResizing(false);
      setIsDragging(false);
      dragStartRef.current = null;
      if (isDetailDragging) {
        setIsDetailDragging(false);
        detailWindowDragRef.current = null;
      }
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isOpen, isResizing, isDragging, dockedSide, panelWidth, isDocked, isDetailDragging]);

  const handleResizeStart = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    event.preventDefault();
    setIsResizing(true);
  }, []);

  const handleDragStart = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (event.button !== 0) {
      return;
    }
    event.preventDefault();

    const startX = isDocked
      ? dockedSide === "left"
        ? 0
        : window.innerWidth - panelWidth
      : floatingPosition.x;
    const startY = isDocked ? 0 : floatingPosition.y;

    dragStartRef.current = {
      x: event.clientX,
      y: event.clientY,
      startX,
      startY
    };
    setIsDragging(true);
  }, [isDocked, dockedSide, panelWidth, floatingPosition]);

  const handleDetailDragStart = useCallback((event: React.MouseEvent<HTMLDivElement>) => {
    if (event.button !== 0 || !detailWindowAlertId) {
      return;
    }
    event.preventDefault();

    detailWindowDragRef.current = {
      x: event.clientX,
      y: event.clientY,
      startX: detailWindowPosition.x,
      startY: detailWindowPosition.y
    };
    setIsDetailDragging(true);
  }, [detailWindowAlertId, detailWindowPosition]);

  const handleCloseDetailWindow = useCallback(() => {
    setDetailWindowAlertId(null);
    setIsDetailDragging(false);
    detailWindowDragRef.current = null;
  }, []);

  const handleSelectAlert = useCallback((alertId: string) => {
    setActiveAlertId(prev => {
      if (prev === alertId) {
        setDetailWindowAlertId(null);
        return null;
      }

      setDetailWindowAlertId(alertId);

      if (typeof window !== 'undefined') {
        const viewportWidth = window.innerWidth;
        const viewportHeight = window.innerHeight;
        const baseX = isDocked
          ? dockedSide === 'left'
            ? panelWidth + 24
            : Math.max(16, viewportWidth - (panelWidth + DETAIL_WINDOW_WIDTH + 24))
          : floatingPosition.x + FLOATING_WIDTH + 24;
        const xMax = Math.max(16, viewportWidth - DETAIL_WINDOW_WIDTH - 16);
        const baseY = isDocked ? 80 : floatingPosition.y;
        const yMax = Math.max(16, viewportHeight - DETAIL_WINDOW_HEIGHT - 16);
        setDetailWindowPosition({
          x: clamp(baseX, 16, xMax),
          y: clamp(baseY, 16, yMax)
        });
      }

      void ensureDetail(alertId);
      return alertId;
    });
  }, [dockedSide, ensureDetail, floatingPosition, isDocked, panelWidth]);

  const handleDecision = useCallback(async (
    alert: EnrichedAlert,
    decision: HumanGateStatus
  ) => {
    if (updatingAlertId || decision === "pending") {
      return;
    }

    setUpdatingAlertId(alert.id);
    try {
      const detail = await ensureDetail(alert.id);

      if (decision === "accepted") {
        const prompt = buildDesktopPrompt(alert, detail);
        await command(prompt, "human-gate-alert");
      }

      const payload: AlertStatusUpdateRequest = {
        status: decision,
        actor: "human_gate_frontend",
        reason:
          decision === "accepted"
            ? "Alerta aceptada por el operador"
            : "Alerta rechazada por el operador",
        metadata: {
          source: "historical_alerts_dashboard"
        }
      };

      await updateAlertStatus(alert.id, payload);

      setLocalStatuses(prev => ({
        ...prev,
        [alert.id]: decision
      }));

      setDetailsById(prev => {
        const entry = prev[alert.id];
        if (!entry?.data) {
          return prev;
        }
        return {
          ...prev,
          [alert.id]: {
            ...entry,
            data: {
              ...entry.data,
              status: STATUS_LABELS[decision]
            }
          }
        };
      });

      await loadHistoricalData();
      setLocalStatuses(prev => {
        const { [alert.id]: _removed, ...rest } = prev;
        return rest;
      });
    } catch (err) {
      console.error("Error al procesar la decision humana", err);
    } finally {
      setUpdatingAlertId(null);
    }
  }, [ensureDetail, loadHistoricalData, updatingAlertId]);

  const handleShareWithAI = useCallback(async (alertId: string, detail?: HistoricalAlertDetailDto) => {
    if (!onShareWithAI) {
      return;
    }
    onShareWithAI(alertId, detail ?? null);
  }, [onShareWithAI]);

  const handleRefresh = useCallback(() => {
    void loadHistoricalData();
  }, [loadHistoricalData]);

  if (!isOpen) {
    return null;
  }

  const activeAlert = activeAlertId
    ? enrichedAlerts.find(alert => alert.id === activeAlertId)
    : null;

  const activeDetailState = activeAlert ? detailsById[activeAlert.id] : undefined;
  const activeDetail = activeDetailState?.data;
  const pendingCount = enrichedAlerts.filter(alert => alert.humanStatus === "pending").length;

  const detailWindowState = detailWindowAlertId ? detailsById[detailWindowAlertId] : undefined;
  const detailWindowDetail = detailWindowState?.data;
  const detailWindowLoading = Boolean(detailWindowAlertId && detailWindowState?.loading && !detailWindowDetail);
  const detailWindowError = detailWindowState?.error;
  const detailWindowAlert = detailWindowAlertId ? enrichedAlerts.find(alert => alert.id === detailWindowAlertId) : null;
  const branchInfo = detailWindowDetail?.sucursal ?? detailWindowAlert?.sucursal ?? null;
  const deviceInfo = detailWindowDetail?.dispositivo ?? detailWindowAlert?.dispositivo ?? null;
  const deviceEntries: HistoricalAlertDeviceInfo[] = deviceInfo
    ? Array.isArray(deviceInfo)
      ? deviceInfo
      : [deviceInfo]
    : [];

  const overlayStyle: React.CSSProperties = isDocked
    ? {
        top: 0,
        left: dockedSide === "left" ? 0 : "auto",
        right: dockedSide === "right" ? 0 : "auto",
        width: `${panelWidth}px`,
        height: "100vh"
      }
    : {
        top: `${floatingPosition.y}px`,
        left: `${floatingPosition.x}px`,
        width: `${FLOATING_WIDTH}px`,
        height: `${FLOATING_HEIGHT}px`
      };

  return (
    <>
      <div className={styles.backdrop} />
      <div
        ref={overlayRef}
        className={`${styles.overlay} ${isDocked ? "" : styles.overlayFloating}`.trim()}
        style={overlayStyle}
      >
        {isDocked && (
          <div
            className={styles.resizeHandle}
            style={{ [dockedSide === "left" ? "right" : "left"]: 0 }}
            onMouseDown={handleResizeStart}
          />
        )}
        <div className={styles.shell}>
          <div
            className={styles.header}
            onMouseDown={handleDragStart}
          >
            <div className={styles.headerInfo}>
              <span className={styles.headerTitle}>Alertas Human Gate</span>
              <span className={styles.headerSubtitle}>
                {pendingCount} pendientes | {enrichedAlerts.length} totales
              </span>
            </div>
            <div className={styles.headerActions}>
              <button
                type="button"
                className={styles.headerButton}
                onMouseDown={event => event.stopPropagation()}
                onClick={handleRefresh}
                aria-label="Recargar alertas"
              >
                <ArrowPathIcon width={16} height={16} aria-hidden />
              </button>
              <button
                type="button"
                className={styles.headerButton}
                onMouseDown={event => event.stopPropagation()}
                onClick={onClose}
              >
                X
              </button>
            </div>
          </div>

          <div className={styles.list}>
            {loading ? (
              <div className={styles.stateMessage}>Cargando alertas...</div>
            ) : error ? (
              <div className={styles.errorMessage}>{error}</div>
            ) : enrichedAlerts.length === 0 ? (
              <div className={styles.stateMessage}>No hay alertas registradas</div>
            ) : (
              enrichedAlerts.map(alert => {
                const detailState = detailsById[alert.id];
                const detail = detailState?.data;
                const isActive = alert.id === activeAlertId;
                const preview = buildAlertPreview(alert, isActive ? activeDetail : detail);
                const isUpdating = updatingAlertId === alert.id;
                const statusClassKey = `status${alert.humanStatus.charAt(0).toUpperCase() + alert.humanStatus.slice(1)}`;
                const statusClassName = (styles as Record<string, string>)[statusClassKey] ?? styles.statusPending;

                return (
                  <div
                    key={alert.id}
                    className={`${styles.card} ${isActive ? styles.cardActive : ""}`.trim()}
                  >
                    <button
                      type="button"
                      className={styles.cardButton}
                      onClick={() => handleSelectAlert(alert.id)}
                    >
                      <span
                        className={styles.priorityStripe}
                        style={{ backgroundColor: alert.priorityColor }}
                      />
                      <div className={styles.cardMain}>
                        <div className={styles.cardHeader}>
                          <span className={styles.cardTitle}>{alert.title}</span>
                          <span
                            className={`${styles.statusBadge} ${statusClassName}`.trim()}
                          >
                            {STATUS_LABELS[alert.humanStatus]}
                          </span>
                        </div>
                        <div className={styles.cardMeta}>
                          <span>{formatTimestamp(alert.timestamp)}</span>
                          <span>{alert.priority}</span>
                        </div>
                        <p className={styles.cardSummary}>{preview}</p>
                      </div>
                    </button>

                    {isActive && (
                      <div className={styles.cardExpanded}>
                        <div className={styles.cardControls}>
                          {onShareWithAI && (
                            <button
                              type="button"
                              className={styles.secondaryButton}
                              onClick={event => {
                                event.stopPropagation();
                                void handleShareWithAI(alert.id, detail ?? null);
                              }}
                            >
                              Compartir con AI
                            </button>
                          )}
                          {alert.humanStatus === "pending" ? (
                            <>
                              <button
                                type="button"
                                className={`${styles.actionButton} ${styles.rejectButton}`}
                                disabled={isUpdating}
                                onClick={event => {
                                  event.stopPropagation();
                                  void handleDecision(alert, "rejected");
                                }}
                              >
                                Rechazar
                              </button>
                              <button
                                type="button"
                                className={`${styles.actionButton} ${styles.acceptButton}`}
                                disabled={isUpdating}
                                onClick={event => {
                                  event.stopPropagation();
                                  void handleDecision(alert, "accepted");
                                }}
                              >
                                Aceptar
                              </button>
                            </>
                          ) : (
                            <span className={styles.statusNote}>Decision registrada</span>
                          )}
                        </div>

                        <div className={styles.cardNote}>
                          {detailState?.loading ? (
                            <span>Cargando detalle...</span>
                          ) : detailState?.error ? (
                            <span>{detailState.error}</span>
                          ) : (
                            <span>Abre el detalle priorizado para revisar hipotesis e impacto.</span>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })
            )}
          </div>
        </div>
      {detailWindowAlertId && (
        <div
          className={styles.detailFloatingWindow}
          style={{ left: `${detailWindowPosition.x}px`, top: `${detailWindowPosition.y}px` }}
        >
          <div
            className={`${styles.detailFloatingHeader} ${isDetailDragging ? styles.detailFloatingHeaderDragging : ''}`.trim()}
            onMouseDown={handleDetailDragStart}
          >
            <div className={styles.detailFloatingTitle}>
              <span className={styles.detailFloatingOverline}>Detalle priorizado</span>
              <span className={styles.detailFloatingName}>
                {detailWindowAlert?.title ?? 'Alerta seleccionada'}
              </span>
            </div>
            <button
              type="button"
              className={styles.detailFloatingClose}
              onMouseDown={event => event.stopPropagation()}
              onClick={handleCloseDetailWindow}
            >
              X
            </button>
          </div>
          <div className={styles.detailFloatingBody}>
            {detailWindowLoading ? (
              <div className={styles.stateMessage}>Cargando informacion...</div>
            ) : detailWindowError ? (
              <div className={styles.errorMessage}>{detailWindowError}</div>
            ) : (
              <>


                <div className={styles.detailFloatingSection}>
                  <span className={styles.sectionLabel}>Mensaje</span>
                  <p className={styles.detailText}>
                    {detailWindowAlert?.title ?? 'Sin informacion disponible'}
                  </p>
                </div>

                <div className={styles.detailFloatingSection}>
                  <span className={styles.sectionLabel}>Hipotesis</span>
                  <p className={styles.detailText}>
                    {detailWindowDetail?.description ?? detailWindowDetail?.root_cause ?? 'Sin informacion disponible'}
                  </p>
                </div>

                <div className={styles.detailFloatingSection}>
                  <span className={styles.sectionLabel}>Impacto</span>
                  <p className={styles.detailText}>
                    {detailWindowDetail?.risk_assessment ?? 'Sin informacion disponible'}
                  </p>
                </div>

                <div className={styles.detailFloatingSection}>
                  <span className={styles.sectionLabel}>Acciones sugeridas</span>
                  <p className={styles.detailText}>
                    {detailWindowDetail?.acciones ?? 'Sin accion sugerida'}
                  </p>
                </div>

                <div className={styles.detailFloatingMeta}>
                  <span className={styles.detailFloatingChip}>
                    {detailWindowAlert?.priority ?? 'Prioridad N/D'}
                  </span>
                  <span className={styles.detailFloatingChip}>
                    {detailWindowAlert?.humanStatus ? STATUS_LABELS[detailWindowAlert.humanStatus] : 'Estado N/D'}
                  </span>
                  <span className={styles.detailFloatingChip}>
                    {detailWindowAlert?.timestamp ? formatTimestamp(detailWindowAlert.timestamp) : 'Sin fecha'}
                  </span>
                </div>

                {branchInfo && (
                  <div className={styles.detailFloatingSection}>
                    <span className={styles.sectionLabel}>Sucursal</span>
                    <div className={styles.detailFloatingMetrics}>
                      <div className={styles.detailMetricRow}>
                        <span className={styles.detailMetricLabel}>ID</span>
                        <span className={styles.detailMetricValue}>{branchInfo.sucursal_id}</span>
                      </div>
                      {branchInfo.nombre && (
                        <div className={styles.detailMetricRow}>
                          <span className={styles.detailMetricLabel}>Nombre</span>
                          <span className={styles.detailMetricValue}>{branchInfo.nombre}</span>
                        </div>
                      )}
                      <div className={styles.detailMetricRow}>
                        <span className={styles.detailMetricLabel}>Saldo disponible</span>
                        <span className={styles.detailMetricValue}>
                          {formatCurrencyValue(branchInfo.saldo_total)}
                        </span>
                      </div>
                      <div className={styles.detailMetricRow}>
                        <span className={styles.detailMetricLabel}>Caja teorica</span>
                        <span className={styles.detailMetricValue}>
                          {formatCurrencyValue(branchInfo.caja_teorica)}
                        </span>
                      </div>
                      <div className={styles.detailMetricRow}>
                        <span className={styles.detailMetricLabel}>Cobertura</span>
                        <span className={styles.detailMetricValue}>
                          {formatPercentValue(branchInfo.saldo_cobertura_pct)}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                {deviceEntries.length > 0 && (
                  <div className={styles.detailFloatingSection}>
                    <span className={styles.sectionLabel}>Dispositivos</span>
                    <div className={styles.detailDeviceTable}>
                      <div className={styles.detailDeviceHeader}>
                        <span>Tipo</span>
                        <span>Saldo</span>
                        <span>Capacidad</span>
                        <span>Cobertura</span>
                      </div>
                      {deviceEntries.map((entry, index) => (
                        <React.Fragment key={`detail-device-${index}`}>
                          <div className={styles.detailDeviceRow}>
                            <span>{entry.tipo ?? 'N/D'}</span>
                            <span>{formatCurrencyValue(entry.saldo_total)}</span>
                            <span>{formatCurrencyValue(entry.caja_teorica)}</span>
                            <span>{formatPercentValue(entry.saldo_cobertura_pct)}</span>
                          </div>
                          {entry.latitud !== null && entry.latitud !== undefined && entry.longitud !== null && entry.longitud !== undefined && (
                            <div className={styles.detailDeviceFootnote}>
                              Coordenadas: {`${entry.latitud.toFixed(4)}, ${entry.longitud.toFixed(4)}`}
                            </div>
                          )}
                        </React.Fragment>
                      ))}
                    </div>
                  </div>
                )}
                {detailWindowDetail?.datos_clave && detailWindowDetail.datos_clave.length > 0 && (
                  <div className={styles.detailFloatingSection}>
                    <span className={styles.sectionLabel}>Datos clave</span>
                    <ul className={styles.detailList}>
                      {detailWindowDetail.datos_clave.map((item, index) => (
                        <li key={`detail-window-dato-${index}`}>{item}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      </div>
    </>
  );
}




