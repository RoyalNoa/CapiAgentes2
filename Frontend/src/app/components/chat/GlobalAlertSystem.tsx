'use client';

import React from 'react';
import { useGlobalAlert } from '@/app/contexts/GlobalAlertContext';
import AlertToggleButton from './AlertToggleButton';
import GlobalAlertOverlay from './GlobalAlertOverlay';

export default function GlobalAlertSystem() {
  const {
    alerts,
    unreadCount,
    isOpen,
    setIsOpen,
    markAsRead,
    toggleExpanded,
    executeAction,
    clearAll
  } = useGlobalAlert();

  return (
    <>
      {/* Alert Toggle Button */}
      <AlertToggleButton
        onClick={() => setIsOpen(!isOpen)}
        alertCount={unreadCount}
        criticalCount={alerts.filter(alert => alert.priority === 'critical').length}
        isActive={isOpen}
        position="top-left"
      />

      {/* Alert Overlay */}
      <GlobalAlertOverlay
        isOpen={isOpen}
        setIsOpen={setIsOpen}
        alerts={alerts}
        onMarkAsRead={markAsRead}
        onToggleExpanded={toggleExpanded}
        onExecuteAction={executeAction}
        onClearAll={clearAll}
      />
    </>
  );
}