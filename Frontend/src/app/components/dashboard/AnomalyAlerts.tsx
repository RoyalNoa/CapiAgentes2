/**
 * AnomalyAlerts Component - Panel de alertas y anomalías
 * Muestra alertas críticas ordenadas por severidad con acciones rápidas
 */

'use client';

import React, { useState, useEffect } from 'react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { AnomalyData } from '../../services/dashboardService';

interface AnomalyAlertsProps {
  data: AnomalyData[];
  isLoading?: boolean;
  onResolve?: (anomalyId: string) => void;
  onViewDetails?: (anomalyId: string) => void;
}

// Configuración de severidad
const severityConfig = {
  high: {
    color: 'bg-red-100 text-red-800 border-red-200',
    icon: '🚨',
    bgColor: 'bg-red-50',
    label: 'Alta'
  },
  medium: {
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    icon: '⚠️',
    bgColor: 'bg-yellow-50',
    label: 'Media'
  },
  low: {
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    icon: 'ℹ️',
    bgColor: 'bg-blue-50',
    label: 'Baja'
  }
};

// Componente de severity badge
const SeverityBadge: React.FC<{ severity: AnomalyData['severity'] }> = ({ severity }) => {
  const config = severityConfig[severity];
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${config.color}`}>
      <span className="mr-1">{config.icon}</span>
      {config.label}
    </span>
  );
};

// Componente de anomalía individual
const AnomalyItem: React.FC<{
  anomaly: AnomalyData;
  onResolve?: (id: string) => void;
  onViewDetails?: (id: string) => void;
}> = ({ anomaly, onResolve, onViewDetails }) => {
  const [isResolving, setIsResolving] = useState(false);
  const config = severityConfig[anomaly.severity];

  const handleResolve = async () => {
    setIsResolving(true);
    try {
      await onResolve?.(anomaly.id);
    } finally {
      setIsResolving(false);
    }
  };

  const timeAgo = (timestamp: string) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (days > 0) return `hace ${days} día${days > 1 ? 's' : ''}`;
    if (hours > 0) return `hace ${hours} hora${hours > 1 ? 's' : ''}`;
    return `hace ${minutes} minuto${minutes > 1 ? 's' : ''}`;
  };

  return (
    <div className={`p-4 rounded-lg border-l-4 ${config.bgColor} border-l-${anomaly.severity === 'high' ? 'red' : anomaly.severity === 'medium' ? 'yellow' : 'blue'}-400`}>
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <div className="flex items-center space-x-2 mb-2">
            <SeverityBadge severity={anomaly.severity} />
            <span className="text-xs text-gray-500 font-medium">
              Sucursal {anomaly.branch}
            </span>
            <span className="text-xs text-gray-400">•</span>
            <span className="text-xs text-gray-500">
              {timeAgo(anomaly.timestamp)}
            </span>
          </div>
          
          <h4 className="text-sm font-semibold text-gray-900 mb-1">
            {anomaly.type}
          </h4>
          
          <p className="text-sm text-gray-600 leading-relaxed">
            {anomaly.description}
          </p>
        </div>
        
        <div className="flex items-center space-x-2 ml-4">
          {onViewDetails && (
            <button
              onClick={() => onViewDetails(anomaly.id)}
              className="px-3 py-1 text-xs font-medium text-blue-600 hover:text-blue-500 transition-colors"
            >
              Ver detalles
            </button>
          )}
          
          {onResolve && (
            <button
              onClick={handleResolve}
              disabled={isResolving}
              className="px-3 py-1 text-xs font-medium text-green-600 hover:text-green-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isResolving ? 'Resolviendo...' : 'Resolver'}
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

// Componente de loading
const LoadingComponent: React.FC = () => (
  <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
    <div className="flex items-center justify-between mb-6">
      <div>
        <div className="h-5 bg-gray-300 rounded w-48 mb-2"></div>
        <div className="h-4 bg-gray-300 rounded w-64"></div>
      </div>
      <div className="flex space-x-2">
        <div className="h-8 w-20 bg-gray-300 rounded"></div>
        <div className="h-8 w-24 bg-gray-300 rounded"></div>
      </div>
    </div>
    
    <div className="space-y-4">
      {[1, 2, 3].map(i => (
        <div key={i} className="p-4 bg-gray-50 rounded-lg border-l-4 border-l-gray-300">
          <div className="flex items-center space-x-2 mb-3">
            <div className="h-5 w-16 bg-gray-300 rounded-full"></div>
            <div className="h-4 w-20 bg-gray-300 rounded"></div>
            <div className="h-4 w-24 bg-gray-300 rounded"></div>
          </div>
          <div className="h-4 bg-gray-300 rounded w-3/4 mb-2"></div>
          <div className="h-4 bg-gray-300 rounded w-full"></div>
        </div>
      ))}
    </div>
  </div>
);

export const AnomalyAlerts: React.FC<AnomalyAlertsProps> = ({
  data,
  isLoading = false,
  onResolve,
  onViewDetails
}) => {
  const [filter, setFilter] = useState<AnomalyData['severity'] | 'all'>('all');
  const [showResolved, setShowResolved] = useState(false);

  if (isLoading) {
    return <LoadingComponent />;
  }

  // Filtrar datos
  const filteredData = data.filter(item => {
    if (filter !== 'all' && item.severity !== filter) return false;
    return true;
  });

  // Ordenar por severidad y tiempo
  const sortedData = filteredData.sort((a, b) => {
    const severityOrder = { high: 3, medium: 2, low: 1 };
    const severityDiff = severityOrder[b.severity] - severityOrder[a.severity];
    if (severityDiff !== 0) return severityDiff;
    
    return new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime();
  });

  // Estadísticas
  const stats = {
    high: data.filter(item => item.severity === 'high').length,
    medium: data.filter(item => item.severity === 'medium').length,
    low: data.filter(item => item.severity === 'low').length,
    total: data.length
  };

  if (data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-gray-900">Alertas y Anomalías</h3>
            <p className="text-sm text-gray-600">Monitoreo de eventos críticos</p>
          </div>
        </div>
        
        <div className="flex items-center justify-center h-32 text-gray-500">
          <div className="text-center">
            <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm font-medium text-green-600">¡Excelente! No hay alertas activas</p>
            <p className="text-xs text-gray-500 mt-1">Todos los sistemas funcionan correctamente</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Alertas y Anomalías</h3>
          <p className="text-sm text-gray-600">
            {stats.total} alerta{stats.total !== 1 ? 's' : ''} activa{stats.total !== 1 ? 's' : ''}
          </p>
        </div>
        
        <div className="flex items-center space-x-2">
          {/* Filtro */}
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as typeof filter)}
            className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="all">Todas</option>
            <option value="high">Alta severidad</option>
            <option value="medium">Media severidad</option>
            <option value="low">Baja severidad</option>
          </select>
          
          {/* Botón de refrescar */}
          <button
            onClick={() => window.location.reload()}
            className="p-2 text-gray-500 hover:text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
            title="Refrescar alertas"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>
        </div>
      </div>

      {/* Stats summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-red-50 p-4 rounded-lg border border-red-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-red-900">Críticas</p>
              <p className="text-2xl font-bold text-red-600">{stats.high}</p>
            </div>
            <div className="text-2xl">🚨</div>
          </div>
        </div>
        
        <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-yellow-900">Medias</p>
              <p className="text-2xl font-bold text-yellow-600">{stats.medium}</p>
            </div>
            <div className="text-2xl">⚠️</div>
          </div>
        </div>
        
        <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-blue-900">Bajas</p>
              <p className="text-2xl font-bold text-blue-600">{stats.low}</p>
            </div>
            <div className="text-2xl">ℹ️</div>
          </div>
        </div>
        
        <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-medium text-gray-900">Total</p>
              <p className="text-2xl font-bold text-gray-600">{stats.total}</p>
            </div>
            <div className="text-2xl">📊</div>
          </div>
        </div>
      </div>

      {/* Alerts list */}
      {sortedData.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <p className="text-sm">No hay alertas que coincidan con el filtro seleccionado</p>
        </div>
      ) : (
        <div className="space-y-4 max-h-96 overflow-y-auto">
          {sortedData.map(anomaly => (
            <AnomalyItem
              key={anomaly.id}
              anomaly={anomaly}
              onResolve={onResolve}
              onViewDetails={onViewDetails}
            />
          ))}
        </div>
      )}

      {/* Footer */}
      <TimestampFooter />
    </div>
  );
};

export default AnomalyAlerts;

// Footer separado para manejar fecha sin provocar hydration mismatch
const TimestampFooter: React.FC = () => {
  const [stamp, setStamp] = useState<string | null>(null);
  useEffect(() => {
    // Se calcula sólo en cliente después de montar
    setStamp(format(new Date(), 'PPpp', { locale: es }));
  }, []);
  return (
    <div className="mt-6 pt-4 border-t border-gray-100 text-center">
      <p className="text-xs text-gray-500" suppressHydrationWarning>
        Última actualización: {stamp || '—'}
      </p>
    </div>
  );
};