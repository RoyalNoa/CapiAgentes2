/**
 * Dashboard Layout - Layout específico para las páginas del dashboard ejecutivo
 * Incluye estilos específicos y configuraciones para el dashboard
 */

import React from 'react';
import './dashboard.css';

export const metadata = {
  title: 'Dashboard Ejecutivo | Gestión de Distribución de Efectivo',
  description: 'Panel de control ejecutivo para la gestión y monitoreo de distribución de efectivo en sucursales',
};

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export default function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="dashboard-container">
      {children}
    </div>
  );
}