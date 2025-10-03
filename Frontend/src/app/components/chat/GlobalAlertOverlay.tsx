'use client';

import React, { useState, useRef, useCallback, useEffect } from 'react';

// Design tokens consistent with chat
const THEME = {
  colors: {
    primary: '#00e5ff',
    primaryAlt: '#7df9ff',
    success: '#12d48a',
    warning: '#7df9ff',
    error: '#ff6b6b',
    text: '#e6f1ff',
    textMuted: '#8aa0c5',
    bg: '#0a0f1c',
    panel: 'rgba(14, 22, 38, 0.85)',
    border: '#1d2b4a'
  },
  spacing: { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24 },
  fonts: {
    heading: "'Orbitron', ui-sans-serif, system-ui, sans-serif",
    ui: "'Inter', ui-sans-serif, system-ui, sans-serif"
  }
} as const;

// Enhanced Alert interfaces
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
  context: {
    details: string;
    metadata: Record<string, any>;
    affectedEntities: string[];
    rootCause?: string;
    recommendation?: string;
  };
  actions: AlertAction[];
  tags?: string[];
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

interface GlobalAlertOverlayProps {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  alerts: Alert[];
  onMarkAsRead: (id: string) => void;
  onToggleExpanded: (id: string) => void;
  onExecuteAction: (alertId: string, actionId: string) => void;
  onClearAll: () => void;
}

export default function GlobalAlertOverlay({
  isOpen,
  setIsOpen,
  alerts,
  onMarkAsRead,
  onToggleExpanded,
  onExecuteAction,
  onClearAll
}: GlobalAlertOverlayProps) {
  // HUD movement state (same as chat)
  const [isResizing, setIsResizing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: 100, y: 150 });
  const [isDocked, setIsDocked] = useState(false);
  const [alertWidth, setAlertWidth] = useState(380); // Increased for better UX
  const [alertPosition, setAlertPosition] = useState<'left' | 'right'>('right');
  const dragStartRef = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);

  // Handle resize functionality
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isResizing) {
      const viewportWidth = window.innerWidth;
      let newWidth;

      if (isDocked && alertPosition === 'right') {
        newWidth = viewportWidth - e.clientX;
      } else if (isDocked && alertPosition === 'left') {
        newWidth = e.clientX;
      } else {
        return;
      }

      newWidth = Math.max(350, Math.min(newWidth, viewportWidth * 0.5));
      setAlertWidth(newWidth);
    }

    if (isDragging && dragStartRef.current) {
      const deltaX = e.clientX - dragStartRef.current.x;
      const deltaY = e.clientY - dragStartRef.current.y;

      const newX = dragStartRef.current.startX + deltaX;
      const newY = dragStartRef.current.startY + deltaY;

      // Auto-dock logic
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const dockThreshold = 50;

      if (newX < dockThreshold) {
        setIsDocked(true);
        setAlertPosition('left');
        setPosition({ x: 0, y: 0 });
      } else if (newX + alertWidth > viewportWidth - dockThreshold) {
        setIsDocked(true);
        setAlertPosition('right');
        setPosition({ x: viewportWidth - alertWidth, y: 0 });
      } else {
        setIsDocked(false);
        const constrainedX = Math.max(0, Math.min(newX, viewportWidth - alertWidth));
        const constrainedY = Math.max(0, Math.min(newY, viewportHeight - 500));
        setPosition({ x: constrainedX, y: constrainedY });
      }
    }
  }, [isResizing, isDragging, alertPosition, alertWidth, isDocked]);

  const handleMouseUp = useCallback(() => {
    setIsResizing(false);
    setIsDragging(false);
    dragStartRef.current = null;
  }, []);

  const handleDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsDragging(true);
    dragStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      startX: position.x,
      startY: position.y
    };
  }, [position]);

  // Add event listeners
  useEffect(() => {
    if (isResizing || isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing, isDragging, handleMouseMove, handleMouseUp]);

  // Format timestamp
  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Get alert type config
  const getAlertTypeConfig = (type: Alert['type'], priority: Alert['priority']) => {
    const baseConfig = {
      info: { color: THEME.colors.primary, icon: 'ℹ', bgColor: THEME.colors.primary + '15' },
      success: { color: THEME.colors.success, icon: '✓', bgColor: THEME.colors.success + '15' },
      warning: { color: THEME.colors.primaryAlt, icon: '⚠', bgColor: THEME.colors.primaryAlt + '15' },
      error: { color: THEME.colors.error, icon: '✗', bgColor: THEME.colors.error + '15' }
    }[type];

    // Intensity based on priority
    const intensity = {
      low: '10',
      medium: '15',
      high: '20',
      critical: '30'
    }[priority];

    return {
      ...baseConfig,
      bgColor: baseConfig.color + intensity,
      borderColor: baseConfig.color + (priority === 'critical' ? '60' : '40')
    };
  };

  // Get priority indicator
  const getPriorityIndicator = (priority: Alert['priority']) => {
    const config = {
      low: { dots: 1, color: THEME.colors.textMuted },
      medium: { dots: 2, color: THEME.colors.primaryAlt },
      high: { dots: 3, color: THEME.colors.primary },
      critical: { dots: 4, color: THEME.colors.error }
    }[priority];

    return (
      <div style={{ display: 'flex', gap: '2px', alignItems: 'center' }}>
        {Array.from({ length: config.dots }).map((_, i) => (
          <div key={i} style={{
            width: '3px',
            height: '3px',
            borderRadius: '50%',
            backgroundColor: config.color,
            boxShadow: `0 0 4px ${config.color}40`
          }} />
        ))}
      </div>
    );
  };

  // Render action button
  const renderActionButton = (action: AlertAction, alertId: string) => {
    const getVariantStyle = (variant?: string) => {
      switch (variant) {
        case 'primary':
          return {
            background: `linear-gradient(135deg, ${THEME.colors.primary}, ${THEME.colors.primaryAlt})`,
            color: THEME.colors.bg,
            border: `1px solid ${THEME.colors.primary}60`
          };
        case 'danger':
          return {
            background: `linear-gradient(135deg, ${THEME.colors.error}, ${THEME.colors.error}80)`,
            color: THEME.colors.text,
            border: `1px solid ${THEME.colors.error}60`
          };
        default:
          return {
            background: 'rgba(0, 0, 0, 0.2)',
            color: THEME.colors.text,
            border: `1px solid ${THEME.colors.border}`
          };
      }
    };

    const style = getVariantStyle(action.variant);

    return (
      <button
        key={action.id}
        onClick={() => onExecuteAction(alertId, action.id)}
        title={action.description}
        style={{
          ...style,
          padding: '6px 12px',
          borderRadius: '6px',
          fontSize: '10px',
          fontFamily: THEME.fonts.ui,
          fontWeight: '600',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          display: 'flex',
          alignItems: 'center',
          gap: '4px'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'translateY(-1px)';
          e.currentTarget.style.boxShadow = `0 4px 12px ${style.border.match(/#[\w]+/)?.[0] || THEME.colors.primary}30`;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'translateY(0)';
          e.currentTarget.style.boxShadow = 'none';
        }}
      >
        {action.type === 'chat' && '💬'}
        {action.type === 'button' && '⚡'}
        {action.type === 'link' && '🔗'}
        <span>{action.label}</span>
      </button>
    );
  };

  // Render individual alert
  const renderAlert = (alert: Alert) => {
    const config = getAlertTypeConfig(alert.type, alert.priority);
    const isExpanded = alert.expanded;

    return (
      <div
        key={alert.id}
        style={{
          marginBottom: 0,
          opacity: alert.read ? 0.7 : 1,
          transition: 'all 0.3s ease'
        }}
      >
        {/* Alert Header - Always Visible */}
        <div
          onClick={() => onToggleExpanded(alert.id)}
          style={{
            display: 'flex',
            alignItems: 'flex-start',
            gap: '12px',
            padding: '12px 16px',
            background: config.bgColor,
            border: `1px solid ${config.borderColor}`,
            borderRadius: isExpanded ? '8px 8px 0 0' : '8px',
            cursor: 'pointer',
            position: 'relative',
            transition: 'all 0.2s ease'
          }}
        >
          {/* Priority & Type Indicator */}
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '4px',
            minWidth: '24px'
          }}>
            <div style={{
              width: '20px',
              height: '20px',
              borderRadius: '4px',
              background: `linear-gradient(135deg, ${config.color}, ${config.color}80)`,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '8px',
              fontFamily: THEME.fonts.heading,
              color: THEME.colors.bg,
              boxShadow: `0 0 8px ${config.color}40`
            }}>
              {alert.agent.charAt(0).toUpperCase()}
            </div>
            {getPriorityIndicator(alert.priority)}
          </div>

          {/* Alert Content */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '4px'
            }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}>
                <span style={{
                  fontSize: '10px',
                  color: THEME.colors.textMuted,
                  fontFamily: THEME.fonts.ui,
                  letterSpacing: '0.05em',
                  textTransform: 'uppercase'
                }}>
                  {alert.agent}
                </span>
                <span style={{
                  fontSize: '9px',
                  color: THEME.colors.textMuted + '80',
                  fontFamily: THEME.fonts.ui
                }}>
                  {formatTime(alert.timestamp)}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {!alert.read && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onMarkAsRead(alert.id);
                    }}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: THEME.colors.textMuted,
                      fontSize: '12px',
                      cursor: 'pointer',
                      padding: '2px 4px'
                    }}
                  >
                    ✓
                  </button>
                )}
                <div style={{
                  fontSize: '12px',
                  color: THEME.colors.textMuted,
                  transform: isExpanded ? 'rotate(180deg)' : 'rotate(0deg)',
                  transition: 'transform 0.2s ease'
                }}>
                  ▼
                </div>
              </div>
            </div>

            <h4 style={{
              fontSize: '12px',
              fontWeight: '600',
              color: THEME.colors.text,
              fontFamily: THEME.fonts.ui,
              margin: '0 0 4px 0',
              lineHeight: '1.3'
            }}>
              {alert.title}
            </h4>

            <p style={{
              fontSize: '11px',
              color: THEME.colors.text,
              fontFamily: THEME.fonts.ui,
              margin: '0',
              lineHeight: '1.4',
              opacity: 0.9
            }}>
              {alert.message}
            </p>

            {/* Tags */}
            {alert.tags && alert.tags.length > 0 && (
              <div style={{
                display: 'flex',
                gap: '4px',
                marginTop: '8px',
                flexWrap: 'wrap'
              }}>
                {alert.tags.map(tag => (
                  <span key={tag} style={{
                    fontSize: '9px',
                    padding: '2px 6px',
                    background: config.color + '20',
                    color: config.color,
                    borderRadius: '3px',
                    fontFamily: THEME.fonts.ui,
                    letterSpacing: '0.02em'
                  }}>
                    {tag}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Expanded Content */}
        {isExpanded && (
          <div style={{
            background: THEME.colors.panel,
            border: `1px solid ${config.borderColor}`,
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            padding: '16px',
            animation: 'expandIn 0.2s ease-out'
          }}>
            {/* Detailed Context */}
            <div style={{
              marginBottom: '16px',
              padding: '12px',
              background: 'rgba(0, 0, 0, 0.2)',
              borderRadius: '6px',
              borderLeft: `3px solid ${config.color}`
            }}>
              <div style={{
                fontSize: '10px',
                color: THEME.colors.textMuted,
                fontFamily: THEME.fonts.heading,
                marginBottom: '6px',
                letterSpacing: '0.1em'
              }}>
                FULL CONTEXT
              </div>
              <p style={{
                fontSize: '11px',
                color: THEME.colors.text,
                fontFamily: THEME.fonts.ui,
                lineHeight: '1.4',
                margin: '0 0 8px 0'
              }}>
                {alert.context.details}
              </p>

              {/* Metadata Grid */}
              {Object.keys(alert.context.metadata).length > 0 && (
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
                  gap: '8px',
                  marginTop: '8px'
                }}>
                  {Object.entries(alert.context.metadata).map(([key, value]) => (
                    <div key={key} style={{
                      fontSize: '10px',
                      fontFamily: THEME.fonts.ui
                    }}>
                      <div style={{
                        color: THEME.colors.textMuted,
                        marginBottom: '2px'
                      }}>
                        {key}
                      </div>
                      <div style={{
                        color: THEME.colors.text,
                        fontWeight: '600'
                      }}>
                        {String(value)}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Affected Entities */}
              {alert.context.affectedEntities.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{
                    fontSize: '10px',
                    color: THEME.colors.textMuted,
                    fontFamily: THEME.fonts.ui,
                    marginBottom: '4px'
                  }}>
                    Affected: {alert.context.affectedEntities.join(', ')}
                  </div>
                </div>
              )}

              {/* Root Cause & Recommendation */}
              {alert.context.rootCause && (
                <div style={{
                  marginTop: '8px',
                  padding: '8px',
                  background: THEME.colors.error + '10',
                  borderRadius: '4px'
                }}>
                  <div style={{
                    fontSize: '9px',
                    color: THEME.colors.error,
                    fontWeight: '600',
                    marginBottom: '2px'
                  }}>
                    ROOT CAUSE
                  </div>
                  <div style={{
                    fontSize: '10px',
                    color: THEME.colors.text,
                    fontFamily: THEME.fonts.ui
                  }}>
                    {alert.context.rootCause}
                  </div>
                </div>
              )}

              {alert.context.recommendation && (
                <div style={{
                  marginTop: '8px',
                  padding: '8px',
                  background: THEME.colors.success + '10',
                  borderRadius: '4px'
                }}>
                  <div style={{
                    fontSize: '9px',
                    color: THEME.colors.success,
                    fontWeight: '600',
                    marginBottom: '2px'
                  }}>
                    RECOMMENDATION
                  </div>
                  <div style={{
                    fontSize: '10px',
                    color: THEME.colors.text,
                    fontFamily: THEME.fonts.ui
                  }}>
                    {alert.context.recommendation}
                  </div>
                </div>
              )}
            </div>

            {/* Actionable Buttons */}
            {alert.actions.length > 0 && (
              <div>
                <div style={{
                  fontSize: '10px',
                  color: THEME.colors.textMuted,
                  fontFamily: THEME.fonts.heading,
                  marginBottom: '8px',
                  letterSpacing: '0.1em'
                }}>
                  ACTIONS
                </div>
                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '8px'
                }}>
                  {alert.actions.map(action => renderActionButton(action, alert.id))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    );
  };

  if (!isOpen) return null;

  return (
    <>
      {/* Alert Floating Panel */}
      <div
        ref={overlayRef}
        style={{
          position: 'fixed',
          left: isDocked ? (alertPosition === 'left' ? 0 : 'auto') : `${position.x}px`,
          right: isDocked && alertPosition === 'right' ? 0 : 'auto',
          top: isDocked ? 0 : `${position.y}px`,
          width: isDocked ? `${alertWidth}px` : '380px',
          height: isDocked ? '100vh' : '520px',
          zIndex: 1055,
          pointerEvents: 'auto',
          transition: isDragging ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          filter: isDocked ? 'none' : `drop-shadow(0 0 20px ${THEME.colors.primary}20)`
        }}
      >
        {/* Resize handle - only show when docked */}
        {isDocked && (
          <div
            style={{
              position: 'absolute',
              [alertPosition === 'left' ? 'right' : 'left']: 0,
              top: 0,
              bottom: 0,
              width: '4px',
              cursor: 'ew-resize',
              background: `${THEME.colors.primary}20`,
              opacity: 0,
              transition: 'opacity 0.2s ease'
            }}
            onMouseDown={handleResizeStart}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
          />
        )}

        {/* Alert Container */}
        <div style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: isDocked
            ? 'linear-gradient(135deg, rgba(0, 8, 17, 0.95), rgba(0, 17, 34, 0.95))'
            : 'linear-gradient(135deg, rgba(0, 8, 17, 0.98), rgba(0, 17, 34, 0.98))',
          border: `1px solid ${THEME.colors.primary}60`,
          borderRadius: isDocked ? '0' : '8px',
          boxShadow: isDocked
            ? 'none'
            : `0 0 30px ${THEME.colors.primary}20, inset 0 1px 0 ${THEME.colors.primary}30`,
          fontFamily: THEME.fonts.ui
        }}>
          {/* Alert Header with drag handle */}
          <div
            onMouseDown={handleDragStart}
            style={{
              padding: '12px 16px',
              background: 'linear-gradient(135deg, rgba(0, 17, 34, 0.9), rgba(0, 34, 51, 0.9))',
              borderBottom: `1px solid ${THEME.colors.primary}40`,
              cursor: isDragging ? 'grabbing' : 'grab',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              userSelect: 'none'
            }}
          >
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <div style={{
                width: '4px',
                height: '4px',
                backgroundColor: THEME.colors.primary,
                borderRadius: '50%',
                boxShadow: `0 0 4px ${THEME.colors.primary}`,
                animation: alerts.some(a => !a.read) ? 'pulse 2s infinite' : 'none'
              }} />
              <span style={{
                color: THEME.colors.primaryAlt,
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.1em',
                fontFamily: THEME.fonts.heading
              }}>
                ALERTS
              </span>
              <div style={{
                padding: '2px 6px',
                background: alerts.filter(a => !a.read).length > 0 ? THEME.colors.primary + '30' : 'transparent',
                borderRadius: '3px',
                fontSize: '8px',
                fontFamily: THEME.fonts.heading,
                color: THEME.colors.primary
              }}>
                {alerts.filter(a => !a.read).length} NEW
              </div>
            </div>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              {alerts.length > 0 && (
                <button
                  onClick={onClearAll}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: THEME.colors.textMuted,
                    fontSize: '9px',
                    cursor: 'pointer',
                    padding: '2px 6px',
                    fontFamily: THEME.fonts.ui
                  }}
                >
                  Clear All
                </button>
              )}
              <button
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: `${THEME.colors.primaryAlt}60`,
                  fontSize: '12px',
                  cursor: 'pointer',
                  padding: '2px 4px',
                  fontFamily: THEME.fonts.heading
                }}
              >
                ×
              </button>
            </div>
          </div>

          {/* Alerts content */}
          <div style={{
            flex: 1,
            overflowY: 'auto',
            padding: '16px',
            paddingRight: '12px',
            scrollbarWidth: 'thin',
            scrollbarColor: `${THEME.colors.primary}60 transparent`
          }}>
            {alerts.length === 0 ? (
              <div style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                height: '100%',
                flexDirection: 'column',
                gap: '12px'
              }}>
                <div style={{
                  width: '8px',
                  height: '8px',
                  backgroundColor: THEME.colors.primary,
                  borderRadius: '50%',
                  boxShadow: `0 0 16px ${THEME.colors.primary}`,
                  opacity: 0.6
                }} />
                <div style={{
                  color: THEME.colors.textMuted,
                  fontSize: '11px',
                  fontFamily: THEME.fonts.ui,
                  textAlign: 'center'
                }}>
                  No alerts
                </div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {alerts.map(renderAlert)}
              </div>
            )}
          </div>
        </div>
      </div>

      <style jsx>{`
        /* Enhanced scrollbar styling */
        div::-webkit-scrollbar {
          width: 6px;
        }
        div::-webkit-scrollbar-track {
          background: transparent;
        }
        div::-webkit-scrollbar-thumb {
          background: linear-gradient(
            to bottom,
            ${THEME.colors.primary}60,
            ${THEME.colors.primary}40,
            ${THEME.colors.primary}60
          );
          border-radius: 3px;
          box-shadow: 0 0 4px ${THEME.colors.primary}30;
        }
        div::-webkit-scrollbar-thumb:hover {
          background: linear-gradient(
            to bottom,
            ${THEME.colors.primary}80,
            ${THEME.colors.primary}60,
            ${THEME.colors.primary}80
          );
        }

        @keyframes pulse {
          0%, 100% {
            opacity: 1;
            transform: scale(1);
          }
          50% {
            opacity: 0.6;
            transform: scale(0.95);
          }
        }

        @keyframes expandIn {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
      `}</style>
    </>
  );
}
