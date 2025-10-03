/**
 * Ruta: Frontend/src/app/components/HUD/ActiveEventsPanel.tsx
 * Descripción: Panel de eventos activos del sistema sin "Active Events" title
 * Estado: Activo
 * Autor: Claude Code
 * Última actualización: 2025-09-14
 */

'use client';

import React from 'react';
import styles from './ActiveEventsPanel.module.css';

interface Event {
  id: string;
  type: string;
  timestamp: string;
  data?: any;
  agent?: string;
}

interface ActiveEventsPanelProps {
  events: Event[];
  isConnected: boolean;
}

export const ActiveEventsPanel: React.FC<ActiveEventsPanelProps> = ({
  events,
  isConnected
}) => {
  const formatTimestamp = (timestamp: string): string => {
    try {
      const date = new Date(timestamp);
      return date.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return 'INVALID';
    }
  };

  const getEventTypeColor = (type: string): string => {
    const typeMap: Record<string, string> = {
      'agent_start': '#00ff88',
      'agent_end': '#00ffff',
      'node_transition': '#ffaa00',
      'error': '#ff3333',
      'connection': '#0099cc',
      'disconnect': '#ff3333'
    };
    return typeMap[type] || '#8aa0c5';
  };

  const getEventIcon = (type: string): string => {
    const iconMap: Record<string, string> = {
      'agent_start': '▶',
      'agent_end': '◼',
      'node_transition': '↔',
      'error': '⚠',
      'connection': '🔗',
      'disconnect': '❌'
    };
    return iconMap[type] || '●';
  };

  // Filtrar eventos reales de agentes y mostrar los últimos 15
  const agentEvents = events.filter(event =>
    event.type.includes('agent') ||
    event.type.includes('node') ||
    event.agent ||
    (event.data && event.data.agent)
  );

  const recentEvents = agentEvents.slice(-15).reverse();

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>SYSTEM EVENTS</h2>
        <div className={styles.controls}>
          <div className={styles.connectionBadge} data-connected={isConnected}>
            {isConnected ? 'LIVE' : 'OFFLINE'}
          </div>
          <span className={styles.eventCount}>{recentEvents.length}/15</span>
        </div>
      </div>

      <div className={styles.content}>
        {recentEvents.length === 0 ? (
          <div className={styles.noEvents}>
            <div className={styles.noEventsIcon}>📡</div>
            <span>Waiting for system events...</span>
            <div className={styles.connectionStatus}>
              Connection: {isConnected ? 'Active' : 'Disconnected'}
            </div>
          </div>
        ) : (
          <div className={styles.eventsList}>
            {recentEvents.map((event, index) => (
              <div key={event.id || index} className={styles.eventItem}>
                <div className={styles.eventHeader}>
                  <div className={styles.eventType}>
                    <span
                      className={styles.eventIcon}
                      style={{ color: getEventTypeColor(event.type) }}
                    >
                      {getEventIcon(event.type)}
                    </span>
                    <span className={styles.eventTypeText}>
                      {event.type.replace(/_/g, ' ').toUpperCase()}
                    </span>
                  </div>
                  <span className={styles.eventTime}>
                    {formatTimestamp(event.timestamp)}
                  </span>
                </div>

                {event.agent && (
                  <div className={styles.eventAgent}>
                    Agent: <span className={styles.agentName}>{event.agent}</span>
                  </div>
                )}

                {event.data && (
                  <div className={styles.eventData}>
                    {typeof event.data === 'object' ? (
                      Object.entries(event.data).slice(0, 2).map(([key, value]) => (
                        <div key={key} className={styles.dataItem}>
                          <span className={styles.dataKey}>{key}:</span>
                          <span className={styles.dataValue}>
                            {typeof value === 'string' ? value : JSON.stringify(value)}
                          </span>
                        </div>
                      ))
                    ) : (
                      <div className={styles.dataItem}>
                        <span className={styles.dataValue}>{String(event.data)}</span>
                      </div>
                    )}
                  </div>
                )}

                <div className={styles.eventIndicator}
                     style={{ backgroundColor: getEventTypeColor(event.type) }} />
              </div>
            ))}
          </div>
        )}
      </div>

      <div className={styles.footer}>
        <div className={styles.statusIndicator}>
          <div
            className={styles.statusDot}
            style={{ backgroundColor: isConnected ? '#00ff88' : '#ff3333' }}
          />
          <span>MONITORING</span>
        </div>
      </div>
    </div>
  );
};

export default ActiveEventsPanel;