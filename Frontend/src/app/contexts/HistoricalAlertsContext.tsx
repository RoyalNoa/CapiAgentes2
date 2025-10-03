"use client";

import React, {
  createContext,
  useContext,
  useState,
  useEffect,
  useMemo,
  useCallback,
  ReactNode
} from 'react';
import {
  getHistoricalAlertsSummary,
  getHistoricalAlertAIContext,
  HistoricalAlertSummaryDto,
  HistoricalAlertAIContext as HistoricalAlertAIContextDto
} from '@/app/utils/orchestrator/client';

interface HistoricalAlertsContextType {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  alerts: HistoricalAlertSummaryDto[];
  loading: boolean;
  error: string | null;
  totalAlerts: number;
  criticalAlerts: number;
  loadHistoricalData: () => Promise<void>;
  shareAlertWithAI: (alertId: string) => Promise<void>;
}

const HistoricalAlertsContext = createContext<HistoricalAlertsContextType | undefined>(undefined);

interface HistoricalAlertsProviderProps {
  children: ReactNode;
}

function formatNumber(value: number | null | undefined, options: Intl.NumberFormatOptions = {}): string {
  if (value === null || value === undefined) {
    return 'N/D';
  }
  return new Intl.NumberFormat('en-US', options).format(value);
}

function buildAIContextMessage(alertId: string, context: HistoricalAlertAIContextDto): string {
  const summary = context.alert_summary ?? {};
  const analysis = context.ai_analysis ?? {};
  const operations = context.operational_context ?? { affected_entities: [], pending_tasks: 0 };
  const actions = Array.isArray(context.recommended_actions) ? context.recommended_actions : [];

  const entityLines = (operations.affected_entities ?? [])
    .map((entity) => {
      const name = entity?.entity_name ?? entity?.entity_type ?? 'Unknown';
      const impact = entity?.impact_level ? ` (impact: ${entity.impact_level})` : '';
      return `- ${name}${impact}`;
    });

  const affectedEntities = entityLines.length > 0 ? entityLines.join('\n') : '- No registered entities';

  const actionLines = actions.map((action, index) => {
    const title = action?.title ?? `Action ${index + 1}`;
    const priority = action?.priority !== undefined ? `P${action.priority}` : 'P?';
    const team = action?.team ? `Team: ${action.team}` : 'Team N/D';
    const status = action?.status ?? 'status N/D';
    const progress = action?.progress !== undefined ? `progress ${Math.round(action.progress * 100)}%` : '';
    const meta = [team, status, progress].filter(Boolean).join(' | ');
    const details = action?.description ? `
    Detail: ${action.description}` : '';
    return `- [${priority}] ${title} (${meta})${details}`;
  });

  const recommendedActions = actionLines.length > 0 ? actionLines.join('\n') : '- No recommended actions';

  const fraudProbability = analysis.fraud_probability !== undefined && analysis.fraud_probability !== null
    ? `${Math.round(analysis.fraud_probability * 100)}%`
    : 'N/D';

  const confidence = summary.confidence !== undefined && summary.confidence !== null
    ? `${Math.round(summary.confidence * 100)}%`
    : 'N/D';

  return [
    `ALERT ${summary.code ?? alertId}`,
    `Title: ${summary.title ?? 'N/D'}`,
    `Priority: ${summary.priority ?? 'N/D'}`,
    `Financial impact: ${formatNumber(summary.financial_impact, { style: 'currency', currency: summary.currency ?? 'USD' })}`,
    `Model confidence: ${confidence}`,
    '',
    `Root cause: ${analysis.root_cause ?? 'N/D'}`,
    `Fraud probability: ${fraudProbability}`,
    `Trend analysis: ${analysis.trend_analysis ?? 'N/D'}`,
    `Risk assessment: ${analysis.risk_assessment ?? 'N/D'}`,
    '',
    'Affected entities:',
    affectedEntities,
    `Pending tasks: ${operations.pending_tasks ?? 0} | Operational status: ${operations.status ?? 'N/D'}`,
    '',
    'Recommended actions:',
    recommendedActions,
    '',
    'Please review this alert and respond with:',
    '1. Immediate strategic recommendations',
    '2. Key risks to monitor',
    '3. Coordinated actions with owners',
    '4. Indicators to confirm resolution',
    '5. Preventive measures to avoid recurrence'
  ].join('\n');
}

export function HistoricalAlertsProvider({ children }: HistoricalAlertsProviderProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [alerts, setAlerts] = useState<HistoricalAlertSummaryDto[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadHistoricalData = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getHistoricalAlertsSummary({ limit: 100 });
      setAlerts(Array.isArray(data) ? data : []);
      setError(null);
    } catch (err: any) {
      console.error('Error loading historical alerts data:', err);
      setAlerts([]);
      setError(err?.message ?? 'Unable to fetch historical alerts.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHistoricalData();
  }, [loadHistoricalData]);

  const totalAlerts = alerts.length;
  const criticalAlerts = useMemo(
    () => alerts.filter((alert) => {
      const priority = alert.priority?.toLowerCase();
      return priority === 'critical' || priority === 'critica';
    }).length,
    [alerts]
  );

  const shareAlertWithAI = useCallback(async (alertId: string) => {
    try {
      const context = await getHistoricalAlertAIContext(alertId);
      if (typeof window === 'undefined') {
        return;
      }

      const message = buildAIContextMessage(alertId, context);

      window.dispatchEvent(new CustomEvent('add-to-chat', {
        detail: {
          text: message,
          context: {
            alertId,
            source: 'historical_alerts',
            type: 'ai_context'
          }
        }
      }));

      setIsOpen(false);

      window.dispatchEvent(new CustomEvent('open-chat', {
        detail: { focus: true }
      }));
    } catch (err) {
      console.error('Error sharing alert context with AI:', err);
    }
  }, []);

  const contextValue: HistoricalAlertsContextType = {
    isOpen,
    setIsOpen,
    alerts,
    loading,
    error,
    totalAlerts,
    criticalAlerts,
    loadHistoricalData,
    shareAlertWithAI
  };

  return (
    <HistoricalAlertsContext.Provider value={contextValue}>
      {children}
    </HistoricalAlertsContext.Provider>
  );
}

export function useHistoricalAlerts() {
  const context = useContext(HistoricalAlertsContext);
  if (context === undefined) {
    throw new Error('useHistoricalAlerts must be used within a HistoricalAlertsProvider');
  }
  return context;
}

