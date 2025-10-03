/**
 * BranchPerformanceTable Component - Tabla de rendimiento de sucursales
 * Muestra métricas clave de cada sucursal con ordenamiento y filtros
 */

'use client';

import React, { useState, useMemo } from 'react';
import { BranchPerformance } from '../../services/dashboardService';

interface BranchPerformanceTableProps {
  data: BranchPerformance[];
  isLoading?: boolean;
}

type SortField = keyof BranchPerformance;
type SortDirection = 'asc' | 'desc';

// Componente de status badge
const StatusBadge: React.FC<{ status: BranchPerformance['status'] }> = ({ status }) => {
  const statusConfig = {
    excellent: { color: 'bg-green-100 text-green-800', label: 'Excelente' },
    good: { color: 'bg-blue-100 text-blue-800', label: 'Bueno' },
    warning: { color: 'bg-yellow-100 text-yellow-800', label: 'Alerta' },
    critical: { color: 'bg-red-100 text-red-800', label: 'Crítico' }
  };

  const config = statusConfig[status];
  
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${config.color}`}>
      {config.label}
    </span>
  );
};

// Componente de icono de ordenamiento
const SortIcon: React.FC<{ field: SortField; currentSort: { field: SortField; direction: SortDirection } }> = ({
  field,
  currentSort
}) => {
  if (currentSort.field !== field) {
    return (
      <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16V4m0 0L3 8m4-4l4 4m6 0v12m0 0l4-4m-4 4l-4-4" />
      </svg>
    );
  }

  return currentSort.direction === 'asc' ? (
    <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h6m4 0l4-4m0 0l4 4m-4-4v12" />
    </svg>
  ) : (
    <svg className="w-4 h-4 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 4h13M3 8h9m-9 4h9m5-4v12m0 0l-4-4m4 4l4-4" />
    </svg>
  );
};

// Componente de loading skeleton
const LoadingTable: React.FC = () => (
  <div className="bg-white rounded-xl border border-gray-200 p-6 animate-pulse">
    <div className="flex items-center justify-between mb-6">
      <div>
        <div className="h-5 bg-gray-300 rounded w-48 mb-2"></div>
        <div className="h-4 bg-gray-300 rounded w-64"></div>
      </div>
      <div className="h-9 w-32 bg-gray-300 rounded"></div>
    </div>
    
    <div className="overflow-x-auto">
      <table className="min-w-full">
        <thead>
          <tr className="border-b border-gray-200">
            {[1, 2, 3, 4, 5, 6, 7].map(i => (
              <th key={i} className="text-left py-3 px-4">
                <div className="h-4 bg-gray-300 rounded w-20"></div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {[1, 2, 3, 4, 5].map(i => (
            <tr key={i} className="border-b border-gray-100">
              {[1, 2, 3, 4, 5, 6, 7].map(j => (
                <td key={j} className="py-4 px-4">
                  <div className="h-4 bg-gray-200 rounded w-16"></div>
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

export const BranchPerformanceTable: React.FC<BranchPerformanceTableProps> = ({
  data,
  isLoading = false
}) => {
  const [sortConfig, setSortConfig] = useState<{ field: SortField; direction: SortDirection }>({
    field: 'netFlow',
    direction: 'desc'
  });
  const [filterStatus, setFilterStatus] = useState<BranchPerformance['status'] | 'all'>('all');

  // Datos filtrados y ordenados
  const processedData = useMemo(() => {
    let filtered = filterStatus === 'all' ? data : data.filter(item => item.status === filterStatus);
    
    return filtered.sort((a, b) => {
      const aValue = a[sortConfig.field];
      const bValue = b[sortConfig.field];
      
      if (typeof aValue === 'string' && typeof bValue === 'string') {
        return sortConfig.direction === 'asc' 
          ? aValue.localeCompare(bValue)
          : bValue.localeCompare(aValue);
      }
      
      if (typeof aValue === 'number' && typeof bValue === 'number') {
        return sortConfig.direction === 'asc' ? aValue - bValue : bValue - aValue;
      }
      
      return 0;
    });
  }, [data, sortConfig, filterStatus]);

  const handleSort = (field: SortField) => {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'desc' ? 'asc' : 'desc'
    }));
  };

  if (isLoading) {
    return <LoadingTable />;
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V9a2 2 0 012-2h10a2 2 0 012 2v10a2 2 0 01-2 2z" />
            </svg>
            <p className="text-sm">No hay datos de rendimiento disponibles</p>
          </div>
        </div>
      </div>
    );
  }

  // Calcular estadísticas
  const totalIncome = processedData.reduce((sum, item) => sum + item.totalIncome, 0);
  const avgEfficiency = processedData.reduce((sum, item) => sum + item.efficiency, 0) / processedData.length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Rendimiento por Sucursal</h3>
          <p className="text-sm text-gray-600">
            {processedData.length} sucursales • Eficiencia promedio: {avgEfficiency.toFixed(1)}%
          </p>
        </div>
        
        {/* Filter */}
        <select
          value={filterStatus}
          onChange={(e) => setFilterStatus(e.target.value as typeof filterStatus)}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">Todas las sucursales</option>
          <option value="excellent">Excelente</option>
          <option value="good">Bueno</option>
          <option value="warning">Alerta</option>
          <option value="critical">Crítico</option>
        </select>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-blue-50 p-4 rounded-lg">
          <p className="text-sm font-medium text-blue-900">Total Ingresos</p>
          <p className="text-xl font-bold text-blue-600">
            ${new Intl.NumberFormat('es-CO').format(totalIncome)}
          </p>
        </div>
        <div className="bg-green-50 p-4 rounded-lg">
          <p className="text-sm font-medium text-green-900">Mejor Sucursal</p>
          <p className="text-xl font-bold text-green-600">
            {processedData[0]?.branch || 'N/A'}
          </p>
        </div>
        <div className="bg-orange-50 p-4 rounded-lg">
          <p className="text-sm font-medium text-orange-900">Eficiencia Promedio</p>
          <p className="text-xl font-bold text-orange-600">
            {avgEfficiency.toFixed(1)}%
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="min-w-full">
          <thead>
            <tr className="border-b-2 border-gray-200 bg-gray-50">
              <th 
                className="text-left py-3 px-4 font-medium text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('branch')}
              >
                <div className="flex items-center space-x-1">
                  <span>Sucursal</span>
                  <SortIcon field="branch" currentSort={sortConfig} />
                </div>
              </th>
              <th 
                className="text-left py-3 px-4 font-medium text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('cajero')}
              >
                <div className="flex items-center space-x-1">
                  <span>Cajero</span>
                  <SortIcon field="cajero" currentSort={sortConfig} />
                </div>
              </th>
              <th 
                className="text-right py-3 px-4 font-medium text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('totalIncome')}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>Ingresos</span>
                  <SortIcon field="totalIncome" currentSort={sortConfig} />
                </div>
              </th>
              <th 
                className="text-right py-3 px-4 font-medium text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('totalExpenses')}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>Egresos</span>
                  <SortIcon field="totalExpenses" currentSort={sortConfig} />
                </div>
              </th>
              <th 
                className="text-right py-3 px-4 font-medium text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('netFlow')}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>Flujo Neto</span>
                  <SortIcon field="netFlow" currentSort={sortConfig} />
                </div>
              </th>
              <th 
                className="text-right py-3 px-4 font-medium text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('efficiency')}
              >
                <div className="flex items-center justify-end space-x-1">
                  <span>Eficiencia</span>
                  <SortIcon field="efficiency" currentSort={sortConfig} />
                </div>
              </th>
              <th 
                className="text-center py-3 px-4 font-medium text-gray-900 cursor-pointer hover:bg-gray-100 transition-colors"
                onClick={() => handleSort('status')}
              >
                <div className="flex items-center justify-center space-x-1">
                  <span>Estado</span>
                  <SortIcon field="status" currentSort={sortConfig} />
                </div>
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {processedData.map((branch, index) => (
              <tr 
                key={branch.branch}
                className={`hover:bg-gray-50 transition-colors ${
                  index % 2 === 0 ? 'bg-white' : 'bg-gray-50'
                }`}
              >
                <td className="py-4 px-4">
                  <div className="flex items-center">
                    <div className="text-sm font-medium text-gray-900">{branch.branch}</div>
                  </div>
                </td>
                <td className="py-4 px-4">
                  <div className="text-sm text-gray-600 font-mono">{branch.cajero}</div>
                </td>
                <td className="py-4 px-4 text-right">
                  <div className="text-sm font-semibold text-green-600">
                    ${new Intl.NumberFormat('es-CO').format(branch.totalIncome)}
                  </div>
                </td>
                <td className="py-4 px-4 text-right">
                  <div className="text-sm font-semibold text-red-600">
                    ${new Intl.NumberFormat('es-CO').format(branch.totalExpenses)}
                  </div>
                </td>
                <td className="py-4 px-4 text-right">
                  <div className={`text-sm font-bold ${
                    branch.netFlow >= 0 ? 'text-green-600' : 'text-red-600'
                  }`}>
                    ${new Intl.NumberFormat('es-CO').format(branch.netFlow)}
                  </div>
                </td>
                <td className="py-4 px-4 text-right">
                  <div className="flex items-center justify-end">
                    <span className="text-sm font-semibold text-gray-900 mr-2">
                      {branch.efficiency.toFixed(1)}%
                    </span>
                    <div className="w-16 bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          branch.efficiency > 90 ? 'bg-green-500' :
                          branch.efficiency > 70 ? 'bg-blue-500' :
                          branch.efficiency > 50 ? 'bg-yellow-500' :
                          'bg-red-500'
                        }`}
                        style={{ width: `${Math.min(branch.efficiency, 100)}%` }}
                      ></div>
                    </div>
                  </div>
                </td>
                <td className="py-4 px-4 text-center">
                  <StatusBadge status={branch.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination hint */}
      {data.length > 10 && (
        <div className="mt-4 text-center text-sm text-gray-500">
          Mostrando {Math.min(processedData.length, 10)} de {processedData.length} sucursales
        </div>
      )}
    </div>
  );
};

export default BranchPerformanceTable;