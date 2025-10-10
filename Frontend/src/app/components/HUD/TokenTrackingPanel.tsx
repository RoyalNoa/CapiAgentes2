/**
 * Ruta: Frontend/src/app/components/HUD/TokenTrackingPanel.tsx
 * Descripción: Panel Token Metrics - REAL DATA ONLY per ARCHITECTURE.md
 * Estado: Activo - VERSIÓN 3.0.0 (SIMULATION ELIMINATED)
 * Autor: Claude Code
 * Última actualización: 2025-09-15
 */

'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { getTokenTracking, type TokenTrackingDto, type CostTimelinePoint, type CostTimelineAgentPoint } from '@/app/utils/orchestrator/client';
import styles from './TokenTrackingPanel.module.css';

interface TokenTrackingPanelProps {}

const AGENT_COLORS: Record<string, string> = {
  summary: '#0b3d91',
  branch: '#2a9d8f',
  anomaly: '#f4a261',
  capi_gus: '#e76f51',
  capi_desktop: '#6a4c93',
  capi_datab: '#577590',
  capi_noticias: '#ff9f1c',
  heuristic: '#6c757d'
};

const COLOR_PALETTE = ['#0b3d91', '#2a9d8f', '#f4a261', '#e76f51', '#6a4c93', '#577590', '#ff9f1c', '#00b4d8'];
const colorCache = new Map<string, string>();
function resolveAgentColor(agent: string): string {
  if (AGENT_COLORS[agent]) {
    return AGENT_COLORS[agent];
  }
  if (!colorCache.has(agent)) {
    const index = colorCache.size % COLOR_PALETTE.length;
    colorCache.set(agent, COLOR_PALETTE[index]);
  }
  return colorCache.get(agent) ?? '#0b3d91';
}

export default function TokenTrackingPanelV2({}: TokenTrackingPanelProps) {
  const [tokenData, setTokenData] = useState<TokenTrackingDto | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // REAL DATA FETCH - NO SIMULATION
  const fetchTokenData = useCallback(async () => {
    console.log('🔄 [TokenTracking] Starting fetch...');
    setLoading(true);
    setError(null);

    try {
      // Add timeout protection
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Request timeout after 10 seconds')), 10000)
      );

      console.log('📊 [TokenTracking] Calling getTokenTracking API...');
      const data = await Promise.race([getTokenTracking(), timeoutPromise]);
      console.log('✅ [TokenTracking] API Response received:', data);
      setTokenData(data as any);
    } catch (err: any) {
      console.error('❌ [TokenTracking] Error loading token data:', err);
      console.error('❌ [TokenTracking] Error details:', {
        message: err?.message,
        stack: err?.stack,
        type: typeof err
      });
      setError(err?.message || 'Error loading token data');
    } finally {
      console.log('🏁 [TokenTracking] Fetch completed, setting loading=false');
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchTokenData();
    const interval = setInterval(fetchTokenData, 30000); // Update every 30 seconds
    return () => clearInterval(interval);
  }, [fetchTokenData]);


    const formatNumber = (value: number): string => {
    if (!Number.isFinite(value)) return '0';
    return Math.round(value).toLocaleString('en-US');
  };

  const formatCurrency = (value: number): string => '$' + (Number.isFinite(value) ? value.toFixed(4) : '0.0000');

  const formatDateLabel = (isoDate: string): string => {
    try {
      const date = new Date(isoDate);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
      return isoDate;
    }
  };

  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', { hour12: false });
    } catch {
      return 'Invalid';
    }
  };

  // REAL DATA METRICS DISPLAY
  const renderTokenMetrics = () => {
    if (!tokenData) return null;

    const totalTokens = tokenData.total_tokens || 0;
    const totalCost = tokenData.total_cost_usd || 0;

    return (
      <div className={styles.summaryMetrics}>
        <div className={`${styles.metricCard} ${styles.metricCardPrimary}`}>
          <span className={styles.metricLabel}>Total Tokens</span>
          <span className={styles.metricValue}>{formatNumber(totalTokens)}</span>
        </div>
        <div className={`${styles.metricCard} ${styles.metricCardSecondary}`}>
          <span className={styles.metricLabel}>Total Cost</span>
          <span className={styles.metricValue}>{formatCurrency(totalCost)}</span>
        </div>
      </div>
    );
  };

  // REAL DATA AGENT LIST
  const renderAgentBreakdown = () => {
    if (!tokenData?.agents || typeof tokenData.agents !== 'object') return null;

    const agentsArray = Object.entries(tokenData.agents).map(([name, data]: [string, any]) => ({
      name,
      total_tokens: data.total_tokens || 0,
      prompt_tokens: data.prompt_tokens_total || data.prompt_tokens || 0,
      completion_tokens: data.completion_tokens_total || data.completion_tokens || 0,
      cost_usd: data.cost_usd || 0,
      status: data.status || 'idle',
      provider: data.provider || 'openai',
      last_model: data.last_model || null,
      last_seen: data.last_seen || null
    }));

    if (agentsArray.length === 0) {
      return <p className={styles.emptyState}>No agent metrics available.</p>;
    }

    return (
      <div className={styles.agentsList}>
        <h4 className={styles.subBoxTitle}>Agent Breakdown</h4>
        {agentsArray.map(agent => (
          <div key={agent.name} className={styles.agentItem + ' ' + styles.active}>
            <div className={styles.agentInfo}>
              <div
                className={styles.agentDot}
                style={{ backgroundColor: resolveAgentColor(agent.name) }}
              />
              <span className={styles.agentName}>{agent.name}</span>
            </div>
            <div className={styles.agentMetrics}>
              <span className={styles.tokenCount}>{formatNumber(agent.total_tokens)}</span>
              <span className={styles.costValue}>{formatCurrency(agent.cost_usd)}</span>
              <span className={styles.tokenBreakdown}>in {formatNumber(agent.prompt_tokens)} / out {formatNumber(agent.completion_tokens)}</span>
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Cost timeline visualization

const renderCostTimeline = () => {
  const timeline = (tokenData?.cost_timeline ?? []) as CostTimelinePoint[];
  if (!timeline.length) {
    return (
      <div className={styles.chartContainer}>
        <h4 className={styles.subBoxTitle}>Cost Timeline</h4>
        <div className={styles.costChartPlaceholder}>No timeline data available.</div>
      </div>
    );
  }

  const maxDailyCost = Math.max(...timeline.map(point => point.total_cost_usd || 0), 0.0001);

  return (
    <div className={styles.chartContainer}>
      <h4 className={styles.subBoxTitle}>Cost Timeline</h4>
      <div className={styles.timelineGrid}>
        {timeline.map(point => {
          const totalCost = point.total_cost_usd || 0;
          const agentEntries = Object.entries(point.agents || {}) as Array<[string, CostTimelineAgentPoint]>;
          const segments = agentEntries.length
            ? agentEntries
            : [['heuristic', {
                cost_usd: totalCost,
                tokens: point.total_tokens || 0,
                prompt_tokens: point.total_prompt_tokens || 0,
                completion_tokens: point.total_completion_tokens || 0,
              } as CostTimelineAgentPoint]];
          return (
            <div key={point.date} className={styles.timelineBar}>
              <div className={styles.timelineBarStack} title={`${formatDateLabel(point.date)} · ${formatCurrency(totalCost)}`}>
                {segments.map(([agentName, metrics]) => {
                  const basePercent = maxDailyCost ? (metrics.cost_usd / maxDailyCost) * 100 : 0;
                  const heightPercent = metrics.cost_usd > 0 ? Math.min(100, Math.max(2, basePercent)) : 0;
                  return (
                    <div
                      key={`${point.date}-${agentName}`}
                      className={styles.timelineSegment}
                      style={{
                        height: `${heightPercent}%`,
                        backgroundColor: resolveAgentColor(agentName),
                        opacity: metrics.cost_usd > 0 ? 1 : 0.2,
                      }}
                      title={`${agentName} · ${formatCurrency(metrics.cost_usd)} · ${formatNumber(metrics.tokens || 0)} tokens`}
                    />
                  );
                })}
              </div>
              <span className={styles.timelineLabel}>{formatDateLabel(point.date)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};


  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h3 className={styles.title}>Token Tracking</h3>
        </div>
        <div className={styles.loadingContainer}>
          <div className={styles.loadingSpinner}></div>
          <span>Loading real token data...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={styles.container}>
        <div className={styles.header}>
          <h3 className={styles.title}>Token Tracking</h3>
        </div>
        <div className={styles.errorContainer}>
          <div className={styles.errorIcon}>⚠️</div>
          <p>Error: {error}</p>
          <button onClick={fetchTokenData} className={styles.retryBtn}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.metricsBox}>
        <div className={styles.header}>
          <h3 className={styles.title}>Token Metrics</h3>
          <span className={styles.updateTime}>
            {tokenData?.timestamp ? formatTimestamp(tokenData.timestamp) : '--:--:--'}
          </span>
        </div>
        <div className={styles.content}>
          {renderTokenMetrics()}
          {renderAgentBreakdown()}
        </div>
      </div>

      <div className={styles.timelineBox}>
        <div className={styles.header}>
          <h3 className={styles.title}>Cost Timeline</h3>
          <span className={styles.currency}>USD</span>
        </div>
        <div className={styles.timelineContent}>
          {renderCostTimeline()}
        </div>
      </div>
    </div>
  );
}
