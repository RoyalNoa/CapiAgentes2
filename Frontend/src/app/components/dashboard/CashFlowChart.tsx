/**
 * CashFlowChart Component - Gráfico de flujo de caja para el dashboard ejecutivo
 * Muestra la evolución temporal de ingresos vs egresos con análisis de tendencias
 */

'use client';

import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';
import { CashFlowData } from '../../services/dashboardService';

interface CashFlowChartProps {
  data: CashFlowData[];
  isLoading?: boolean;
  height?: number;
}

// Componente de tooltip personalizado
const CustomTooltip: React.FC<any> = ({ active, payload, label }) => {
  if (active && payload && payload.length) {
    const date = new Date(label);
    const formattedDate = format(date, 'PPP', { locale: es });
    
    return (
      <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
        <p className="font-medium text-gray-900 mb-2">{formattedDate}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between space-x-4">
            <div className="flex items-center space-x-2">
              <div 
                className="w-3 h-3 rounded-full" 
                style={{ backgroundColor: entry.color }}
              />
              <span className="text-sm text-gray-600">{entry.name}:</span>
            </div>
            <span className="font-semibold text-sm">
              ${new Intl.NumberFormat('es-CO').format(entry.value)}
            </span>
          </div>
        ))}
        
        {payload.length >= 2 && (
          <div className="mt-2 pt-2 border-t border-gray-100">
            <div className="flex items-center justify-between space-x-4">
              <span className="text-sm text-gray-600 font-medium">Flujo Neto:</span>
              <span className={`font-bold text-sm ${
                payload[0].value - payload[1].value >= 0 ? 'text-green-600' : 'text-red-600'
              }`}>
                ${new Intl.NumberFormat('es-CO').format(payload[0].value - payload[1].value)}
              </span>
            </div>
          </div>
        )}
      </div>
    );
  }
  return null;
};

// Componente de loading skeleton
const LoadingChart: React.FC<{ height: number }> = ({ height }) => (
  <div 
    className="animate-pulse bg-gray-100 rounded-lg flex items-center justify-center"
    style={{ height }}
  >
    <div className="text-center">
      <div className="w-8 h-8 bg-gray-300 rounded-full mx-auto mb-2"></div>
      <div className="h-4 bg-gray-300 rounded w-32"></div>
    </div>
  </div>
);

export const CashFlowChart: React.FC<CashFlowChartProps> = ({ 
  data, 
  isLoading = false, 
  height = 400 
}) => {
  if (isLoading) {
    return <LoadingChart height={height} />;
  }

  if (!data || data.length === 0) {
    return (
      <div 
        className="flex items-center justify-center bg-gray-50 rounded-lg border-2 border-dashed border-gray-300"
        style={{ height }}
      >
        <div className="text-center text-gray-500">
          <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-2a2 2 0 00-2-2H5a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2V9a2 2 0 012-2h2a2 2 0 012 2v10a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <p className="text-sm">No hay datos de flujo de caja disponibles</p>
        </div>
      </div>
    );
  }

  // Usar los datos originales y formatear sólo en render (evita perder el año y problemas al parsear)
  const chartData = data; // cada item.date viene en formato ISO 'YYYY-MM-DD'

  // Calcular estadísticas
  const totalIngresos = data.reduce((sum, item) => sum + item.ingresos, 0);
  const totalEgresos = data.reduce((sum, item) => sum + item.egresos, 0);
  const avgIngreso = totalIngresos / data.length;
  const avgEgreso = totalEgresos / data.length;

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Flujo de Caja</h3>
          <p className="text-sm text-gray-600">Ingresos vs Egresos (últimos 7 días)</p>
        </div>
        
        {/* Mini stats */}
        <div className="flex space-x-6">
          <div className="text-right">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Promedio Ingresos</p>
            <p className="text-sm font-semibold text-green-600">
              ${new Intl.NumberFormat('es-CO').format(avgIngreso)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-500 uppercase tracking-wider">Promedio Egresos</p>
            <p className="text-sm font-semibold text-red-600">
              ${new Intl.NumberFormat('es-CO').format(avgEgreso)}
            </p>
          </div>
        </div>
      </div>

      {/* Chart */}
      <ResponsiveContainer width="100%" height={height}>
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis 
            dataKey="date" 
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
            tickFormatter={(value: string) => {
              const d = new Date(value);
              return isNaN(d.getTime()) ? value : format(d, 'dd/MM', { locale: es });
            }}
          />
          <YAxis 
            tick={{ fontSize: 12 }}
            stroke="#6b7280"
            tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend 
            wrapperStyle={{ fontSize: '14px' }}
            iconType="circle"
          />
          
          <Line 
            type="monotone" 
            dataKey="ingresos" 
            stroke="#10b981"
            strokeWidth={3}
            dot={{ fill: '#10b981', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#10b981', strokeWidth: 2 }}
            name="Ingresos"
          />
          
          <Line 
            type="monotone" 
            dataKey="egresos" 
            stroke="#ef4444"
            strokeWidth={3}
            dot={{ fill: '#ef4444', strokeWidth: 2, r: 4 }}
            activeDot={{ r: 6, stroke: '#ef4444', strokeWidth: 2 }}
            name="Egresos"
          />
          
          <Line 
            type="monotone" 
            dataKey="net" 
            stroke="#3b82f6"
            strokeWidth={2}
            strokeDasharray="5 5"
            dot={{ fill: '#3b82f6', strokeWidth: 2, r: 3 }}
            name="Flujo Neto"
          />
        </LineChart>
      </ResponsiveContainer>

      {/* Bottom summary */}
      <div className="mt-4 pt-4 border-t border-gray-100">
        <div className="grid grid-cols-3 gap-4">
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Ingresos</p>
            <p className="text-lg font-bold text-green-600">
              ${new Intl.NumberFormat('es-CO').format(totalIngresos)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Total Egresos</p>
            <p className="text-lg font-bold text-red-600">
              ${new Intl.NumberFormat('es-CO').format(totalEgresos)}
            </p>
          </div>
          <div className="text-center">
            <p className="text-xs text-gray-500 uppercase tracking-wider mb-1">Flujo Neto</p>
            <p className={`text-lg font-bold ${
              totalIngresos - totalEgresos >= 0 ? 'text-green-600' : 'text-red-600'
            }`}>
              ${new Intl.NumberFormat('es-CO').format(totalIngresos - totalEgresos)}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CashFlowChart;