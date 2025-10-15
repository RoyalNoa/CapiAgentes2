/**
 * Ruta: Frontend/src/app/pages/agentes/page.tsx
 * Descripción: AGENT CONTROL CENTER - Vista alineada al HUD global
 * Estado: Activo
 */

'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import {
  setAgentEnabled,
  getAgentsMetrics,
  getSystemStatus,
  refreshAgents,
  type AgentMetricsDto,
  type SystemStatusDto
} from '@/app/utils/orchestrator/client';
import { useAgentWebSocket } from '@/app/hooks/useAgentWebSocket';

import HUDLayout from '@/app/components/HUD/HUDLayout';
import GraphPanel from '@/app/components/HUD/GraphPanel';
import TokenTrackingPanel from '@/app/components/HUD/TokenTrackingPanel';
import ActiveEventsPanel from '@/app/components/HUD/ActiveEventsPanel';
import AgentRegistrationModal from '@/app/components/HUD/AgentRegistrationModal';
import HistoricalAlertsDashboard from '@/app/components/alerts/HistoricalAlertsDashboard';

import '@/app/ui/hud.css';
import '@/app/ui/hud-enhancements.css';
import styles from './AgentesPage.module.css';

interface ExtendedAgentData {
  name: string;
  enabled: boolean;
  description: string;
  status: 'active' | 'idle' | 'processing' | 'error';
  metrics?: {
    tokens_used: number;
    cost_usd: number;
    requests: number;
    avg_response_time: number;
  };
}

type MetricsSummary = {
  tokens: number;
  cost: number;
  requests: number;
  avgResponse: number;
};

type LiveWorkflowState = {
  sessionId: string | null;
  currentNode?: string | null;
  previousNode?: string | null;
  completedNodes?: string[];
  status?: string;
  step?: number | null;
  snapshot?: Record<string, any> | null;
};

const STATUS_LABEL: Record<ExtendedAgentData['status'], string> = {
  active: 'Active',
  idle: 'Idle',
  processing: 'Processing',
  error: 'Error'
};

const statusClassMap: Record<ExtendedAgentData['status'], string> = {
  active: styles.statusActive,
  idle: styles.statusIdle,
  processing: styles.statusProcessing,
  error: styles.statusError
};

const FALLBACK_AGENTS: ExtendedAgentData[] = [
  {
    name: 'capi_gus',
    enabled: true,
    description: 'Respuestas ejecutivas multi-canal',
    status: 'active',
    metrics: { tokens_used: 18420, cost_usd: 0.0272, requests: 163, avg_response_time: 1.1 }
  },
  {
    name: 'branch',
    enabled: true,
    description: 'Análisis de sucursales y sucursales virtuales',
    status: 'active',
    metrics: { tokens_used: 11280, cost_usd: 0.0164, requests: 108, avg_response_time: 0.8 }
  },
  {
    name: 'anomaly',
    enabled: true,
    description: 'Detección de anomalías transaccionales',
    status: 'processing',
    metrics: { tokens_used: 24560, cost_usd: 0.0368, requests: 224, avg_response_time: 2.0 }
  },
  {
    name: 'scribe',
    enabled: false,
    description: 'Registro de sesiones y auditoría',
    status: 'idle',
    metrics: { tokens_used: 4200, cost_usd: 0.0061, requests: 41, avg_response_time: 0.6 }
  },
  {
    name: 'capi_desktop',
    enabled: true,
    description: 'Automatización en desktop remotos',
    status: 'active',
    metrics: { tokens_used: 19710, cost_usd: 0.0295, requests: 166, avg_response_time: 1.6 }
  },
  {
    name: 'ops_router',
    enabled: true,
    description: 'Orquestador de flujos operativos',
    status: 'processing',
    metrics: { tokens_used: 16590, cost_usd: 0.0246, requests: 138, avg_response_time: 2.4 }
  },
  {
    name: 'risk_guardian',
    enabled: true,
    description: 'Evaluación de riesgos y cumplimiento',
    status: 'active',
    metrics: { tokens_used: 15110, cost_usd: 0.0223, requests: 119, avg_response_time: 1.3 }
  },
  {
    name: 'atlas_mapper',
    enabled: false,
    description: 'Cartografía de conocimiento interno',
    status: 'idle',
    metrics: { tokens_used: 3120, cost_usd: 0.0047, requests: 29, avg_response_time: 0.7 }
  },
  {
    name: 'vector_forge',
    enabled: true,
    description: 'Embeddings y enriquecimiento semántico',
    status: 'processing',
    metrics: { tokens_used: 22870, cost_usd: 0.0348, requests: 192, avg_response_time: 2.7 }
  },
  {
    name: 'comms_bridge',
    enabled: true,
    description: 'Integraciones con canales externos',
    status: 'active',
    metrics: { tokens_used: 10340, cost_usd: 0.0155, requests: 97, avg_response_time: 1.0 }
  },
  {
    name: 'sentinel',
    enabled: false,
    description: 'Monitoreo de seguridad y alertas',
    status: 'error',
    metrics: { tokens_used: 1890, cost_usd: 0.0028, requests: 18, avg_response_time: 0.9 }
  },
  {
    name: 'capi_datab',
    enabled: true,
    description: 'Automatización de bases de datos y ETL',
    status: 'idle',
    metrics: { tokens_used: 5400, cost_usd: 0.0081, requests: 52, avg_response_time: 1.5 }
  }
];

const normalizeGraphStatus = (status: ExtendedAgentData['status']): 'active' | 'idle' =>
  status === 'idle' ? 'idle' : 'active';

export default function AgentesPage() {
  const {
    isConnected,
    events,
    lastEvent,
    lastTransition,
    sessionStates,
    activeSessionId,
    connect,
    disconnect
  } = useAgentWebSocket();

  const [agents, setAgents] = useState<ExtendedAgentData[]>([]);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [systemStatus, setSystemStatus] = useState<SystemStatusDto | null>(null);
  const [agentsMetrics, setAgentsMetrics] = useState<AgentMetricsDto | null>(null);
  const [showAgentModal, setShowAgentModal] = useState(false);
  const [showAlertsPanel, setShowAlertsPanel] = useState(false);

  const loadAgents = useCallback(async () => {
    setLoadingAgents(true);
    try {
      const metricsData = await getAgentsMetrics();
      setAgentsMetrics(metricsData);

      const enrichedAgents: ExtendedAgentData[] = metricsData.agents.map((agent: any) => ({
        ...agent,
        metrics: {
          tokens_used: agent.total_tokens || 0,
          cost_usd: agent.total_cost || 0,
          requests: agent.request_count || 0,
          avg_response_time: agent.avg_response_time || 0
        }
      }));
      setAgents(enrichedAgents);

      const statusData = await getSystemStatus();
      setSystemStatus(statusData);
    } catch (error) {
      console.error('Failed to load agents:', error);
      setAgents(FALLBACK_AGENTS);
    } finally {
      setLoadingAgents(false);
    }
  }, []);

  useEffect(() => {
    const initialize = async () => {
      try {
        await refreshAgents();
      } catch (error) {
        console.warn('Agent refresh failed:', error);
      }
      await loadAgents();
    };

    void initialize();
    const interval = setInterval(() => {
      void loadAgents();
    }, 10000);
    return () => clearInterval(interval);
  }, [loadAgents]);

  const handleAgentToggle = useCallback(async (agentName: string, enabled: boolean) => {
    try {
      await setAgentEnabled(agentName, enabled);
      await loadAgents();
    } catch (error) {
      console.error('Failed to toggle agent:', error);
    }
  }, [loadAgents]);

  const formatTimestamp = (isoString: string): string => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('es-ES', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return 'Invalid time';
    }
  };

  const liveWorkflow = useMemo<LiveWorkflowState | null>(() => {
    if (lastTransition && lastTransition.type === 'node_transition') {
      const sessionId = lastTransition.session_id ?? lastTransition.data?.session_id ?? activeSessionId ?? null;
      const snapshotEntry = sessionId ? sessionStates[sessionId] : undefined;
      const snapshot = snapshotEntry?.snapshot ?? lastTransition.data?.state ?? null;
      const completedNodes = Array.isArray(lastTransition.data?.completed_nodes)
        ? (lastTransition.data?.completed_nodes as string[])
        : [];
      return {
        sessionId,
        currentNode: lastTransition.to ?? lastTransition.data?.to ?? null,
        previousNode: lastTransition.from ?? lastTransition.data?.from ?? null,
        completedNodes,
        status: lastTransition.data?.status,
        step: typeof lastTransition.data?.step === 'number' ? lastTransition.data.step : null,
        snapshot: snapshot ?? null
      };
    }

    if (activeSessionId) {
      const snapshotEntry = sessionStates[activeSessionId];
      const snapshot = snapshotEntry?.snapshot;
      if (snapshot && typeof snapshot === 'object') {
        const nodeData = snapshot as Record<string, any>;
        const completedNodes = Array.isArray(nodeData.completed_nodes) ? (nodeData.completed_nodes as string[]) : [];
        return {
          sessionId: activeSessionId,
          currentNode: typeof nodeData.current_node === 'string' ? nodeData.current_node : null,
          previousNode: typeof nodeData.previous_node === 'string' ? nodeData.previous_node : null,
          completedNodes,
          status: typeof nodeData.status === 'string' ? nodeData.status : undefined,
          step: typeof nodeData.step === 'number' ? nodeData.step : null,
          snapshot: nodeData
        };
      }
    }

    return null;
  }, [lastTransition, activeSessionId, sessionStates]);

  const metricsSummary = useMemo<MetricsSummary>(() => {
    if (!agentsMetrics?.agents?.length) {
      return { tokens: 0, cost: 0, requests: 0, avgResponse: 0 };
    }

    const totals = agentsMetrics.agents;
    const tokens = totals.reduce((sum: number, agent: any) => sum + (agent.total_tokens || 0), 0);
    const cost = totals.reduce((sum: number, agent: any) => sum + (agent.total_cost || 0), 0);
    const requests = totals.reduce((sum: number, agent: any) => sum + (agent.request_count || 0), 0);
    const weightedResponse = totals.reduce((sum: number, agent: any) => {
      const avg = agent.avg_response_time || 0;
      const count = agent.request_count || 0;
      return sum + avg * count;
    }, 0);

    const avgResponse = requests > 0 ? weightedResponse / requests : 0;
    return { tokens, cost, requests, avgResponse };
  }, [agentsMetrics]);

  const activeAgentsCount = systemStatus?.active_agents ?? agents.filter(agent => agent.enabled).length;
  const totalAgentsCount = systemStatus?.total_agents ?? agents.length;
  const offlineAgentsCount = Math.max(totalAgentsCount - activeAgentsCount, 0);
  const lastEventTime = lastEvent?.timestamp ? formatTimestamp(lastEvent.timestamp) : 'N/A';

  const graphAgents = useMemo(() => (
    agents.map(agent => ({
      name: agent.name,
      enabled: agent.enabled,
      description: agent.description,
      status: normalizeGraphStatus(agent.status)
    }))
  ), [agents]);

  const handleAgentSelect = useCallback((agentName: string) => {
    setSelectedAgent(prev => (prev === agentName ? null : agentName));
  }, []);

  const handleGraphAgentSelect = useCallback((agentName: string | null) => {
    setSelectedAgent(agentName ?? null);
  }, []);

  const handleRefreshClick = useCallback(() => {
    void loadAgents();
  }, [loadAgents]);

  const handleOpenAlerts = useCallback(() => {
    setShowAlertsPanel(true);
  }, []);


  /*
  const agentGridContent = agents.length === 0 ? (
    <div className={styles.emptyState}>
      <p>No agents registered yet.</p>
      <button type="button" onClick={() => setShowAgentModal(true)}>
        Register agent
      </button>
    </div>
  ) : (
    <div className={styles.agentGrid}>
      {agents.map(agent => {
        const metrics = agent.metrics;
        const isSelected = agent.name === selectedAgent;

        return (
          <div
            key={agent.name}
            className={`${styles.agentCard} ${isSelected ? styles.agentCardActive : ''}`}
          >
            <div className={styles.agentCardHeader}>
              <div>
                <h3 className={styles.agentName}>{agent.name}</h3>
                <p className={styles.agentDescription}>{agent.description}</p>
              </div>
              <span className={`${styles.agentStatus} ${statusClassMap[agent.status]}`}>
                {STATUS_LABEL[agent.status]}
              </span>
            </div>

            <div className={styles.agentMetricsGrid}>
              <div>
                <span className={styles.metricLabel}>Tokens</span>
                <span className={styles.metricValue}>
                  {metrics ? metrics.tokens_used.toLocaleString('en-US') : 'N/A'}
                </span>
              </div>
              <div>
                <span className={styles.metricLabel}>Cost</span>
                <span className={styles.metricValue}>
                  ${metrics ? metrics.cost_usd.toFixed(4) : '0.0000'}
                </span>
              </div>
              <div>
                <span className={styles.metricLabel}>Requests</span>
                <span className={styles.metricValue}>
                  {metrics ? metrics.requests.toLocaleString('en-US') : '0'}
                </span>
              </div>
              <div>
                <span className={styles.metricLabel}>Avg response</span>
                <span className={styles.metricValue}>
                  {metrics && metrics.avg_response_time > 0 ? `${metrics.avg_response_time.toFixed(1)}s` : 'N/A'}
                </span>
              </div>
            </div>

            <div className={styles.agentCardActions}>
              <button
                type="button"
                className={styles.inspectButton}
                onClick={() => handleAgentSelect(agent.name)}
              >
                {isSelected ? 'Hide details' : 'Inspect'}
              </button>
              <button
                type="button"
                className={`${styles.toggleButton} ${agent.enabled ? styles.toggleEnabled : styles.toggleDisabled}`}
                onClick={() => {
                  void handleAgentToggle(agent.name, !agent.enabled);
                  if (!agent.enabled) {
                    setSelectedAgent(agent.name);
                  }
                }}
                disabled={loadingAgents}
              >
                {agent.enabled ? 'Disable' : 'Enable'}
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
  */
  const agentGridContent = null;
  void agentGridContent;

  return (
    <>
      <HUDLayout
        title="AGENT CONTROL CENTER"
        isConnected={isConnected}
        onConnect={connect}
        onDisconnect={disconnect}
        leftPanel={
          <div className={styles.leftPanelContainer}>
            <TokenTrackingPanel />
          </div>
        }
        centerPanel={
          <div className={styles.centerPanelContainer}>
            <div className={styles.graphSection}>
              <GraphPanel
                agents={graphAgents}
                systemStatus={systemStatus}
                isConnected={isConnected}
                selectedAgent={selectedAgent}
                onSelectAgent={handleGraphAgentSelect}
                events={events}
                onAgentsUpdate={() => { void loadAgents(); }}
                liveFlow={liveWorkflow}
              />
            </div>

            {/* Toolbar central reservada para futuras acciones */}
            {/* agentGridContent reservado para reactivar la grilla de agentes */}
          </div>
        }
        rightPanel={
          <div className={styles.rightPanelContainer}>
            <div className={`${styles.panelBlock} ${styles.panelBlockFlush}`}>
              <ActiveEventsPanel events={events} isConnected={isConnected} />
            </div>
          </div>
        }
      />

      {showAgentModal && (
        <AgentRegistrationModal
          isOpen={showAgentModal}
          onClose={() => setShowAgentModal(false)}
          onSuccess={() => {
            setShowAgentModal(false);
            void loadAgents();
          }}
        />
      )}

      {showAlertsPanel && (
        <HistoricalAlertsDashboard
          isOpen={showAlertsPanel}
          onClose={() => setShowAlertsPanel(false)}
          onShareWithAI={alert => console.log('Share alert with AI:', alert)}
        />
      )}
    </>
  );
}
