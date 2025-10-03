"use client";

import React, { useCallback, useState } from 'react';
import { useHistoricalAlerts } from '@/app/contexts/HistoricalAlertsContext';
import AlertToggleButton from '@/app/components/chat/AlertToggleButton';
import HistoricalAlertsDashboard from './HistoricalAlertsDashboard';

export default function HistoricalAlertsSystem() {
  const [hasError, setHasError] = useState(false);
  const {
    isOpen,
    setIsOpen,
    totalAlerts,
    criticalAlerts,
    loadHistoricalData,
    loading,
    error
  } = useHistoricalAlerts();

  const handleToggle = useCallback(async () => {
    try {
      setHasError(false);
      if (!isOpen) {
        await loadHistoricalData();
      }
      setIsOpen(!isOpen);
    } catch (error) {
      console.error('Error loading historical data:', error);
      setHasError(true);
      // No abrir el panel si hay error
    }
  }, [isOpen, loadHistoricalData, setIsOpen]);

  // Solo mostrar si no hay errores críticos
  if (hasError && error) {
    return null;
  }

  return (
    <>
      {!isOpen && !loading && (
        <AlertToggleButton
          onClick={handleToggle}
          alertCount={totalAlerts}
          criticalCount={criticalAlerts}
          isActive={isOpen}
          position="top-left"
        />
      )}

      <HistoricalAlertsDashboard
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
      />
    </>
  );
}
