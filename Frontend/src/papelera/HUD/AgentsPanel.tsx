/**
 * Ruta: Frontend/src/app/components/HUD/AgentsPanel.tsx
 * Descripción: Panel de agentes con estilo HUD futurista
 * Estado: Activo
 * Autor: Claude Code
 * Última actualización: 2025-09-14
 */

'use client';

import React from 'react';
import styles from './AgentsPanel.module.css';

interface AgentData {
  name: string;
  enabled: boolean;
  description: string;
  status: 'active' | 'idle';
}

interface AgentsPanelProps {
  agents: AgentData[];
  loading: boolean;
  onToggleAgent: (agentName: string, enabled: boolean) => void;
  onSelectAgent: (agentName: string) => void;
  selectedAgent: string | null;
}

export const AgentsPanel: React.FC<AgentsPanelProps> = ({
  agents,
  loading,
  onToggleAgent,
  onSelectAgent,
  selectedAgent
}) => {
  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>ACTIVE AGENTS</h2>
        <div className={styles.badge}>
          {agents.filter(a => a.enabled).length}/{agents.length}
        </div>
      </div>

      <div className={styles.content}>
        {loading ? (
          <div className={styles.loading}>
            <div className={styles.loadingSpinner} />
            <span>Loading agents...</span>
          </div>
        ) : (
          <div className={styles.agentsList}>
            {agents.map((agent) => (
              <div
                key={agent.name}
                className={`${styles.agentCard} ${selectedAgent === agent.name ? styles.selected : ''}`}
                onClick={() => onSelectAgent(agent.name)}
              >
                <div className={styles.agentHeader}>
                  <div className={styles.agentInfo}>
                    <div className={`${styles.statusIndicator} ${styles[agent.status]}`} />
                    <h3 className={styles.agentName}>{agent.name.toUpperCase()}</h3>
                  </div>

                  <label
                    className={styles.switch}
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      checked={agent.enabled}
                      onChange={(e) => onToggleAgent(agent.name, e.target.checked)}
                    />
                    <span className={styles.slider} />
                  </label>
                </div>

                <p className={styles.agentDescription}>{agent.description}</p>

                <div className={styles.agentStats}>
                  <div className={styles.stat}>
                    <span className={styles.statValue}>
                      {agent.enabled ? 'ONLINE' : 'OFFLINE'}
                    </span>
                    <span className={styles.statLabel}>STATUS</span>
                  </div>
                  <div className={styles.stat}>
                    <span className={styles.statValue}>
                      {agent.status.toUpperCase()}
                    </span>
                    <span className={styles.statLabel}>STATE</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default AgentsPanel;