'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

// Enhanced Alert interface with full context and actions
interface Alert {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  priority: 'low' | 'medium' | 'high' | 'critical';
  agent: string;
  title: string;
  message: string;
  timestamp: number;
  read: boolean;
  expanded?: boolean;

  // Full context data
  context: {
    details: string;
    metadata: Record<string, any>;
    affectedEntities: string[];
    rootCause?: string;
    recommendation?: string;
  };

  // Actionable items
  actions: AlertAction[];

  // Visual enhancements
  tags?: string[];
  relatedAlerts?: string[];
}

interface AlertAction {
  id: string;
  type: 'chat' | 'input' | 'button' | 'link';
  label: string;
  description?: string;
  variant?: 'primary' | 'secondary' | 'danger';
  payload?: any;
  autoAddToChat?: boolean;
  chatContext?: string;
}

interface GlobalAlertContextType {
  // Alert state
  alerts: Alert[];
  unreadCount: number;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;

  // Alert management
  addAlert: (alert: Omit<Alert, 'id' | 'timestamp' | 'read' | 'expanded'>) => void;
  markAsRead: (id: string) => void;
  toggleExpanded: (id: string) => void;
  executeAction: (alertId: string, actionId: string) => void;
  clearAll: () => void;

  // Layout
  alertWidth: number;
  setAlertWidth: (width: number) => void;
  alertPosition: 'left' | 'right';
  setAlertPosition: (position: 'left' | 'right') => void;
}

const GlobalAlertContext = createContext<GlobalAlertContextType | undefined>(undefined);

interface GlobalAlertProviderProps {
  children: ReactNode;
}

export function GlobalAlertProvider({ children }: GlobalAlertProviderProps) {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [alertWidth, setAlertWidth] = useState(340);
  const [alertPosition, setAlertPosition] = useState<'left' | 'right'>('right');

  // Calculate unread count
  const unreadCount = alerts.filter(alert => !alert.read).length;

  // Add alert
  const addAlert = (alertData: Omit<Alert, 'id' | 'timestamp' | 'read' | 'expanded'>) => {
    const newAlert: Alert = {
      ...alertData,
      id: `alert-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      timestamp: Date.now(),
      read: false,
      expanded: false
    };

    setAlerts(prev => [newAlert, ...prev].slice(0, 50)); // Keep only last 50 alerts
  };

  // Mark alert as read
  const markAsRead = (id: string) => {
    setAlerts(prev =>
      prev.map(alert =>
        alert.id === id ? { ...alert, read: true } : alert
      )
    );
  };

  // Toggle expanded state
  const toggleExpanded = (id: string) => {
    setAlerts(prev =>
      prev.map(alert =>
        alert.id === id ? { ...alert, expanded: !alert.expanded } : alert
      )
    );
  };

  // Execute alert action
  const executeAction = (alertId: string, actionId: string) => {
    const alert = alerts.find(a => a.id === alertId);
    const action = alert?.actions.find(a => a.id === actionId);

    if (!alert || !action) return;

    // Handle different action types
    switch (action.type) {
      case 'chat':
        // Add context to global chat
        if (action.autoAddToChat && action.chatContext) {
          // Dispatch event to add context to chat
          const event = new CustomEvent('add-to-chat', {
            detail: {
              text: action.chatContext,
              context: {
                alertId: alertId,
                agent: alert.agent,
                title: alert.title
              }
            }
          });
          window.dispatchEvent(event);
        }
        break;

      case 'button':
        // Execute button action
        console.log('Executing action:', action.label, action.payload);
        break;

      case 'link':
        // Open link
        if (action.payload?.url) {
          window.open(action.payload.url, '_blank');
        }
        break;
    }

    // Mark alert as read after action
    markAsRead(alertId);
  };

  // Clear all alerts
  const clearAll = () => {
    setAlerts([]);
  };

  // Simulate professional demo alerts with full context and actions
  useEffect(() => {
    const demoAlerts = [
      {
        type: 'warning' as const,
        priority: 'high' as const,
        agent: 'anomaly',
        title: 'Unusual Transaction Pattern Detected',
        message: 'Detected 15 high-value transactions exceeding normal patterns in Branch Norte',
        context: {
          details: 'Pattern analysis shows transactions between 14:30-16:45 with amounts 340% above average. Transactions originated from 3 different terminals but same card type pattern.',
          metadata: {
            affectedBranch: 'Norte',
            transactionCount: 15,
            amountRange: '$45,000 - $67,500',
            timeWindow: '14:30-16:45',
            deviation: '340%',
            confidence: 0.87
          },
          affectedEntities: ['Branch Norte', 'Terminal T-001', 'Terminal T-003', 'Terminal T-007'],
          rootCause: 'Suspected coordinated transaction pattern - possible fraud or data entry error',
          recommendation: 'Immediate review of transactions and customer verification required'
        },
        actions: [
          {
            id: 'investigate',
            type: 'chat',
            label: 'Investigate Pattern',
            description: 'Add investigation context to chat',
            variant: 'primary',
            autoAddToChat: true,
            chatContext: 'Investigate anomaly: 15 unusual transactions in Branch Norte, amounts $45K-67.5K, 340% above average. Time window: 14:30-16:45. Terminals: T-001, T-003, T-007. Confidence: 87%'
          },
          {
            id: 'block',
            type: 'button',
            label: 'Block Terminals',
            description: 'Temporarily block affected terminals',
            variant: 'danger',
            payload: { action: 'block', terminals: ['T-001', 'T-003', 'T-007'] }
          },
          {
            id: 'report',
            type: 'link',
            label: 'View Full Report',
            description: 'Open detailed anomaly report',
            variant: 'secondary',
            payload: { url: '/reports/anomaly/A-2025-001' }
          }
        ],
        tags: ['Fraud Risk', 'High Value', 'Multi-Terminal']
      },
      {
        type: 'error' as const,
        priority: 'critical' as const,
        agent: 'system',
        title: 'Data Connection Lost',
        message: 'Critical connection failure to primary financial database',
        context: {
          details: 'Connection to primary database server (DB-PROD-01) lost at 15:42. Failover to secondary successful but with 2min data lag. System experiencing degraded performance.',
          metadata: {
            server: 'DB-PROD-01',
            failureTime: '15:42',
            failoverStatus: 'Active',
            dataLag: '2 minutes',
            affectedServices: 4
          },
          affectedEntities: ['Primary Database', 'Real-time Reports', 'Transaction Processing', 'Branch Analytics'],
          rootCause: 'Network connectivity issue between data center and primary database cluster',
          recommendation: 'Monitor secondary systems closely. Prepare for manual data reconciliation once primary connection restored.'
        },
        actions: [
          {
            id: 'monitor',
            type: 'chat',
            label: 'Monitor Systems',
            description: 'Add monitoring context to chat',
            variant: 'primary',
            autoAddToChat: true,
            chatContext: 'System Alert: Primary DB connection lost at 15:42. Running on secondary with 2min lag. Monitor: Transaction Processing, Branch Analytics, Real-time Reports. Need manual reconciliation when restored.'
          },
          {
            id: 'status',
            type: 'link',
            label: 'System Status',
            description: 'Check detailed system status',
            variant: 'secondary',
            payload: { url: '/system/status' }
          }
        ],
        tags: ['Critical', 'Database', 'Network']
      },
      {
        type: 'info' as const,
        priority: 'medium' as const,
        agent: 'branch',
        title: 'Branch Performance Spike',
        message: 'Branch Sur showing exceptional 18% increase in daily volume',
        context: {
          details: 'Branch Sur exceeded daily targets by 18% with particularly strong performance in business accounts (+24%) and loan processing (+31%). Staff efficiency metrics also up 12%.',
          metadata: {
            branch: 'Sur',
            volumeIncrease: '18%',
            businessAccounts: '+24%',
            loanProcessing: '+31%',
            efficiency: '+12%',
            target: 'Exceeded'
          },
          affectedEntities: ['Branch Sur', 'Business Division', 'Loan Department'],
          recommendation: 'Analyze success factors for potential replication across other branches'
        },
        actions: [
          {
            id: 'analyze',
            type: 'chat',
            label: 'Analyze Success',
            description: 'Deep dive into performance factors',
            variant: 'primary',
            autoAddToChat: true,
            chatContext: 'Performance Analysis Request: Branch Sur +18% volume, Business Accounts +24%, Loans +31%, Efficiency +12%. What factors drove this success? How can we replicate across branches?'
          },
          {
            id: 'compare',
            type: 'button',
            label: 'Compare Branches',
            description: 'Generate comparative analysis',
            variant: 'secondary',
            payload: { action: 'compare', baseBranch: 'Sur' }
          }
        ],
        tags: ['Performance', 'Growth', 'Best Practice']
      }
    ];

    // Add demo alerts with delay
    let index = 0;
    const addDemoAlert = () => {
      if (index < demoAlerts.length) {
        addAlert(demoAlerts[index]);
        index++;
        setTimeout(addDemoAlert, 3000);
      }
    };

    // Start adding demo alerts after 2 seconds
    const timeout = setTimeout(addDemoAlert, 2000);
    return () => clearTimeout(timeout);
  }, []);

  // Listen for real agent alerts (you can connect this to your WebSocket or API)
  useEffect(() => {
    // Example of listening for agent events
    const handleAgentAlert = (event: any) => {
      if (event.detail?.type === 'alert') {
        addAlert({
          type: event.detail.alertType || 'info',
          agent: event.detail.agent || 'system',
          title: event.detail.title || 'Agent Notification',
          message: event.detail.message || 'New alert from agent'
        });
      }
    };

    // Listen for custom agent alert events
    window.addEventListener('agent-alert', handleAgentAlert);

    return () => {
      window.removeEventListener('agent-alert', handleAgentAlert);
    };
  }, []);

  const contextValue: GlobalAlertContextType = {
    // State
    alerts,
    unreadCount,
    isOpen,
    setIsOpen,

    // Actions
    addAlert,
    markAsRead,
    toggleExpanded,
    executeAction,
    clearAll,

    // Layout
    alertWidth,
    setAlertWidth,
    alertPosition,
    setAlertPosition
  };

  return (
    <GlobalAlertContext.Provider value={contextValue}>
      {children}
    </GlobalAlertContext.Provider>
  );
}

export function useGlobalAlert() {
  const context = useContext(GlobalAlertContext);
  if (context === undefined) {
    throw new Error('useGlobalAlert must be used within a GlobalAlertProvider');
  }
  return context;
}

// Utility function to dispatch alerts from anywhere in the app
export function dispatchAlert(alertData: Omit<Alert, 'id' | 'timestamp' | 'read'>) {
  const event = new CustomEvent('agent-alert', {
    detail: {
      type: 'alert',
      alertType: alertData.type,
      agent: alertData.agent,
      title: alertData.title,
      message: alertData.message
    }
  });

  window.dispatchEvent(event);
}