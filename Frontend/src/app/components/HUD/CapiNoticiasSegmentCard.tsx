import React from 'react';
import { SEGMENT_KEYS, SEGMENT_LABELS, DEFAULT_SEGMENT_MIN_PRIORITY, type SegmentKey } from '@/app/utils/capiNoticiasSegments';
import styles from './GraphPanel.module.css';

export interface CapiNoticiasSegmentControls {
  config: { segments?: Record<string, CapiSegmentConfig> } | null;
  draft: Record<SegmentKey, number>;
  onChange: (segment: SegmentKey, rawValue: string) => void;
  onReset: () => void;
  onSave: () => void | Promise<void>;
  lastRunDisplay: string | null;
  counts: Record<SegmentKey, number> | null;
  loading: boolean;
  updating: boolean;
  message: string | null;
  error: string | null;
  onReload: () => void | Promise<void>;
}

interface CapiSegmentConfig {
  min_priority?: number;
  lookback_hours?: number;
  lookback_days?: number;
  max_items?: number;
}

interface Props {
  controls?: CapiNoticiasSegmentControls;
}

const CapiNoticiasSegmentCard: React.FC<Props> = ({ controls }) => {
  if (!controls) {
    return null;
  }

  const {
    config,
    draft,
    onChange,
    onReset,
    onSave,
    lastRunDisplay,
    counts,
    loading,
    updating,
    message,
    error,
    onReload,
  } = controls;

  const segmentConfig = (config?.segments ?? {}) as Record<string, CapiSegmentConfig>;
  const hasInvalidValues = SEGMENT_KEYS.some((segment) => !Number.isFinite(draft[segment]));
  const hasChanges = SEGMENT_KEYS.some((segment) => {
    const draftValue = draft[segment];
    const currentValue = segmentConfig[segment]?.min_priority ?? DEFAULT_SEGMENT_MIN_PRIORITY[segment];
    if (!Number.isFinite(draftValue)) {
      return false;
    }
    return Math.abs(draftValue - currentValue) > 0.001;
  });
  const saveDisabled = updating || hasInvalidValues || !hasChanges;

  const handleReload = () => {
    void onReload();
  };

  if (loading) {
    return (
      <div className={styles.segmentCard}>
        <div className={styles.segmentCardLoading}>
          <span>Cargando configuracion...</span>
          <button
            type="button"
            className={styles.segmentCardGhostButton}
            onClick={handleReload}
            disabled={updating}
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className={styles.segmentCard}>
        <div className={styles.segmentCardLoading}>
          <span>No se pudo cargar la configuracion.</span>
          <button
            type="button"
            className={styles.segmentCardGhostButton}
            onClick={handleReload}
            disabled={updating}
          >
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.segmentCard}>
      <div className={styles.segmentCardHeader}>
        <div>
          <span className={styles.segmentCardTitle}>Segmentos destacados</span>
          {lastRunDisplay && (
            <span className={styles.segmentCardSubtitle}>Ultima corrida: {lastRunDisplay}</span>
          )}
        </div>
        {counts && (
          <div className={styles.segmentCardCounts}>
            {SEGMENT_KEYS.map((segment) => (
              <span key={segment} className={styles.segmentCardBadge}>
                {SEGMENT_LABELS[segment]}: {counts[segment] ?? 0}
              </span>
            ))}
          </div>
        )}
      </div>

      <p className={styles.segmentCardDescription}>
        Ajusta el score minimo por segmento para controlar cuantas noticias se conservan. Un umbral alto reduce los items retenidos.
      </p>

      <div className={styles.segmentCardGrid}>
        {SEGMENT_KEYS.map((segment) => {
          const cfg = segmentConfig[segment];
          const draftValue = draft[segment];
          const inputValue = Number.isFinite(draftValue) ? draftValue : '';
          const currentMin = typeof cfg?.min_priority === 'number'
            ? cfg.min_priority
            : DEFAULT_SEGMENT_MIN_PRIORITY[segment];
          const lookback = typeof cfg?.lookback_days === 'number'
            ? `${cfg.lookback_days} dias`
            : typeof cfg?.lookback_hours === 'number'
              ? `${cfg.lookback_hours} horas`
              : null;
          const maxItems = typeof cfg?.max_items === 'number' ? cfg.max_items : null;
          const inputId = `segment-${segment}-min-priority`;

          return (
            <div key={segment} className={styles.segmentCardField}>
              <label htmlFor={inputId} className={styles.segmentCardFieldLabel}>
                {SEGMENT_LABELS[segment]}
              </label>
              <input
                id={inputId}
                type="number"
                step="0.1"
                min={0}
                value={inputValue}
                onChange={(event) => onChange(segment, event.target.value)}
                className={styles.segmentCardInput}
                disabled={updating}
              />
              <div className={styles.segmentCardMeta}>
                <span>Min actual: {currentMin.toFixed(2)}</span>
                {lookback && <span>Ventana: {lookback}</span>}
                {maxItems !== null && <span>Maximo: {maxItems}</span>}
              </div>
              <div className={styles.segmentCardHint}>
                Valor recomendado inicial: {DEFAULT_SEGMENT_MIN_PRIORITY[segment].toFixed(1)}
              </div>
            </div>
          );
        })}
      </div>

      <div className={styles.segmentCardActions}>
        <button
          type="button"
          className={styles.segmentCardPrimaryButton}
          onClick={() => { void onSave(); }}
          disabled={saveDisabled}
        >
          {updating ? 'Guardando...' : 'Guardar umbrales'}
        </button>
        <button
          type="button"
          className={styles.segmentCardGhostButton}
          onClick={onReset}
          disabled={updating}
        >
          Restablecer
        </button>
        <button
          type="button"
          className={styles.segmentCardGhostButton}
          onClick={handleReload}
          disabled={updating}
        >
          Recargar
        </button>
      </div>

      {message && (
        <span className={styles.segmentCardMessage}>{message}</span>
      )}
      {error && (
        <span className={styles.segmentCardError}>{error}</span>
      )}
    </div>
  );
};

export default CapiNoticiasSegmentCard;
