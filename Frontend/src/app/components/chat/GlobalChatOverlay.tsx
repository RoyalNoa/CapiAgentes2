'use client';

import React, { useState, useRef, useCallback } from 'react';
import { FolderIcon, SparklesIcon, ClockIcon } from '@heroicons/react/24/outline';
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';
import { SimpleChatBox } from '.';
import styles from './GlobalChatOverlay.module.css';
import SessionFilesViewer from './SessionFilesViewer';

const HUD_ICON_BUTTON_STYLE: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  width: '24px',
  height: '24px',
  borderRadius: '6px',
  border: '1px solid rgba(0, 255, 255, 0.35)',
  background: 'rgba(0, 255, 255, 0.08)',
  cursor: 'pointer',
  color: 'rgba(0, 255, 255, 0.75)'
};

export default function GlobalChatOverlay() {
  const {
    isOpen,
    setIsOpen,
    chatWidth,
    setChatWidth,
    chatPosition,
    setChatPosition,
    selectedSucursal,
    setSelectedSucursal,
    showSidebar,
    setShowSidebar,
    activeSessionId,
    sessionIds,
    createNewSession,
    switchSession,
    refreshSessions
  } = useGlobalChat();

  // HUD movement state
  const [isResizing, setIsResizing] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [position, setPosition] = useState({ x: 100, y: 100 });
  const [isDocked, setIsDocked] = useState(false);
  const [showSessionViewer, setShowSessionViewer] = useState(false);
  const [showHistoryMenu, setShowHistoryMenu] = useState(false);
  const dragStartRef = useRef<{ x: number; y: number; startX: number; startY: number } | null>(null);
  const overlayRef = useRef<HTMLDivElement>(null);
  const historyMenuRef = useRef<HTMLDivElement>(null);

  // Handle resize functionality
  const handleResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    setIsResizing(true);
  }, []);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (isResizing) {
      const viewportWidth = window.innerWidth;
      let newWidth;

      if (isDocked && chatPosition === 'right') {
        newWidth = viewportWidth - e.clientX;
      } else if (isDocked && chatPosition === 'left') {
        newWidth = e.clientX;
      } else {
        return; // No resize when floating
      }

      newWidth = Math.max(280, Math.min(newWidth, viewportWidth * 0.4));
      setChatWidth(newWidth);
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
        // Dock to left
        setIsDocked(true);
        setChatPosition('left');
        setPosition({ x: 0, y: 0 });
      } else if (newX + chatWidth > viewportWidth - dockThreshold) {
        // Dock to right
        setIsDocked(true);
        setChatPosition('right');
        setPosition({ x: viewportWidth - chatWidth, y: 0 });
      } else {
        // Free floating
        setIsDocked(false);
        const constrainedX = Math.max(0, Math.min(newX, viewportWidth - chatWidth));
        const constrainedY = Math.max(0, Math.min(newY, viewportHeight - 400));
        setPosition({ x: constrainedX, y: constrainedY });
      }
    }
  }, [isResizing, isDragging, chatPosition, chatWidth, isDocked, setChatWidth, setChatPosition]);

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
  React.useEffect(() => {
    if (isResizing || isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing, isDragging, handleMouseMove, handleMouseUp]);

  React.useEffect(() => {
    if (!showHistoryMenu) return;
    const handleOutsideClick = (event: MouseEvent) => {
      if (!historyMenuRef.current) return;
      if (!historyMenuRef.current.contains(event.target as Node)) {
        setShowHistoryMenu(false);
      }
    };
    document.addEventListener('mousedown', handleOutsideClick);
    return () => document.removeEventListener('mousedown', handleOutsideClick);
  }, [showHistoryMenu]);

  if (!isOpen) return null;

  return (
    <>
      {/* HUD Floating Terminal */}
      <div
        ref={overlayRef}
        style={{
          position: 'fixed',
          left: isDocked ? (chatPosition === 'left' ? 0 : 'auto') : `${position.x}px`,
          right: isDocked && chatPosition === 'right' ? 0 : 'auto',
          top: isDocked ? 0 : `${position.y}px`,
          width: isDocked ? `${chatWidth}px` : '320px',
          height: isDocked ? '100vh' : '400px',
          zIndex: 1055,
          pointerEvents: 'auto',
          transition: isDragging ? 'none' : 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          filter: isDocked ? 'none' : 'drop-shadow(0 0 20px rgba(0, 255, 255, 0.2))'
        }}
      >
        {/* Resize handle - only show when docked */}
        {isDocked && (
          <div
            style={{
              position: 'absolute',
              [chatPosition === 'left' ? 'right' : 'left']: 0,
              top: 0,
              bottom: 0,
              width: '4px',
              cursor: 'ew-resize',
              background: 'rgba(0, 255, 255, 0.2)',
              opacity: 0,
              transition: 'opacity 0.2s ease'
            }}
            onMouseDown={handleResizeStart}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '1'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '0'}
          />
        )}

        {/* HUD Terminal Container */}
        <div style={{
          height: '100%',
          display: 'flex',
          flexDirection: 'column',
          background: isDocked
            ? 'linear-gradient(135deg, rgba(0, 8, 17, 0.95), rgba(0, 17, 34, 0.95))'
            : 'linear-gradient(135deg, rgba(0, 8, 17, 0.98), rgba(0, 17, 34, 0.98))',
          border: `1px solid rgba(0, 255, 255, ${isDocked ? '0.3' : '0.5'})`,
          borderRadius: isDocked ? '0' : '8px',
          boxShadow: isDocked
            ? 'none'
            : '0 0 30px rgba(0, 255, 255, 0.2), inset 0 1px 0 rgba(0, 255, 255, 0.3)'
        }}>
          {/* HUD Header with drag handle */}
          <div
            onMouseDown={handleDragStart}
            style={{
              padding: '8px 12px',
              background: 'linear-gradient(135deg, rgba(0, 17, 34, 0.9), rgba(0, 34, 51, 0.9))',
              borderBottom: '1px solid rgba(0, 255, 255, 0.3)',
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
              gap: '6px'
            }}>
              <div style={{
                width: '4px',
                height: '4px',
                backgroundColor: '#00ffff',
                borderRadius: '50%',
                boxShadow: '0 0 4px #00ffff'
              }} />
              <span style={{
                color: '#00ffff',
                fontSize: '10px',
                fontWeight: 600,
                letterSpacing: '0.1em',
                fontFamily: "'Courier New', monospace"
              }}>
                CAPI
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <button
                onMouseDown={(event) => event.stopPropagation()}
                onClick={() => {
                  void createNewSession();
                  setShowHistoryMenu(false);
                }}
                aria-label="Crear nueva sesión"
                style={HUD_ICON_BUTTON_STYLE}
              >
                <SparklesIcon width={14} height={14} aria-hidden />
              </button>
              <div ref={historyMenuRef} style={{ position: 'relative' }}>
                <button
                  onMouseDown={(event) => event.stopPropagation()}
                  onClick={() => {
                    setShowHistoryMenu((prev) => !prev);
                    if (!showHistoryMenu) {
                      void refreshSessions();
                    }
                  }}
                  aria-label="Cambiar historial de sesión"
                  style={{
                    ...HUD_ICON_BUTTON_STYLE,
                    background: showHistoryMenu ? 'rgba(0, 255, 255, 0.15)' : HUD_ICON_BUTTON_STYLE.background,
                  }}
                >
                  <ClockIcon width={14} height={14} aria-hidden />
                </button>
                {showHistoryMenu && (
                  <div
                    style={{
                      position: 'absolute',
                      top: 'calc(100% + 8px)',
                      right: 0,
                      width: '220px',
                      background: 'rgba(0, 17, 34, 0.95)',
                      border: '1px solid rgba(0, 255, 255, 0.25)',
                      borderRadius: '8px',
                      boxShadow: '0 12px 30px rgba(0, 0, 0, 0.45)',
                      padding: '10px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '6px',
                      zIndex: 10,
                    }}
                  >
                    <div
                      style={{
                        fontSize: '11px',
                        letterSpacing: '0.08em',
                        color: 'rgba(0, 255, 255, 0.75)',
                        fontFamily: "'Courier New', monospace",
                        textTransform: 'uppercase',
                      }}
                    >
                      Sesiones disponibles
                    </div>
                    <div style={{ maxHeight: '200px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {sessionIds.map((sessionId) => {
                        const isActive = sessionId === activeSessionId;
                        return (
                          <button
                            key={sessionId}
                            type="button"
                            onClick={() => {
                              switchSession(sessionId);
                              setShowHistoryMenu(false);
                            }}
                            style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              gap: '8px',
                              padding: '6px 8px',
                              background: isActive ? 'rgba(0, 255, 255, 0.12)' : 'rgba(3, 20, 38, 0.9)',
                              border: isActive ? '1px solid rgba(0, 255, 255, 0.45)' : '1px solid rgba(0, 255, 255, 0.18)',
                              borderRadius: '6px',
                              color: 'rgba(214, 239, 255, 0.86)',
                              cursor: 'pointer',
                              fontSize: '12px',
                              fontFamily: "'Inter', sans-serif",
                              transition: 'all 0.2s ease',
                            }}
                          >
                            <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{sessionId}</span>
                            {isActive && (
                              <span style={{ fontSize: '10px', color: 'rgba(0, 255, 255, 0.8)', letterSpacing: '0.08em' }}>
                                activo
                              </span>
                            )}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
              <button
                onMouseDown={(event) => event.stopPropagation()}
                onClick={() => setShowSessionViewer(true)}
                aria-label="Abrir archivos de la IA"
                style={HUD_ICON_BUTTON_STYLE}
              >
                <FolderIcon width={14} height={14} aria-hidden />
              </button>
              <button
                onMouseDown={(event) => event.stopPropagation()}
                onClick={() => setIsOpen(false)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'rgba(0, 255, 255, 0.6)',
                  fontSize: '12px',
                  cursor: 'pointer',
                  padding: '2px 4px',
                  fontFamily: "'Courier New', monospace"
                }}
              >
                ×
              </button>
            </div>
          </div>

          {/* Chat content */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <SimpleChatBox
              sucursal={selectedSucursal}
              onRemoveSucursal={() => setSelectedSucursal(null)}
            />
          </div>
        </div>
      </div>

      {showSessionViewer && (
        <SessionFilesViewer onClose={() => setShowSessionViewer(false)} />
      )}
    </>
  );
}
