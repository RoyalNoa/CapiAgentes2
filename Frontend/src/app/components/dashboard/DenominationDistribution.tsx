/**
 * DenominationDistribution Component - Distribución de denominaciones de efectivo
 * Muestra el porcentaje y valor de cada denominación con visualización tipo donut/bar
 */

'use client';

import React, { useState } from 'react';
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import { DenominationData } from '../../services/dashboardService';

interface DenominationDistributionProps {
  data: DenominationData[];
  isLoading?: boolean;
}

// Colores para las denominaciones
const COLORS = [
  '#3b82f6', // azul
  '#10b981', // verde
  '#f59e0b', // amarillo
  '#ef4444', // rojo
  '#8b5cf6', // púrpura
  '#06b6d4', // cian
];

// Componente de tooltip personalizado
const CustomTooltip: React.FC<any> = ({ active, payload }) => {
  if (active && payload && payload.length) {
    const data = payload[0].payload;
    return (
      <div className="bg-white p-4 border border-gray-200 rounded-lg shadow-lg">
        <h4 className="font-semibold text-gray-900 mb-2">{data.denomination}</h4>
        <div className="space-y-1">
          <p className="text-sm text-gray-600">
            <span className="font-medium">Cantidad:</span> {new Intl.NumberFormat('es-CO').format(data.count)} billetes
          </p>
          <p className="text-sm text-gray-600">
            <span className="font-medium">Valor:</span> ${new Intl.NumberFormat('es-CO').format(data.amount)}
          </p>
          <p className="text-sm text-gray-600">
            <span className="font-medium">Porcentaje:</span> {data.percentage}%
          </p>
        </div>
      </div>
    );
  }
  return null;
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
        <div className="h-8 w-16 bg-gray-300 rounded"></div>
        <div className="h-8 w-16 bg-gray-300 rounded"></div>
      </div>
    </div>
    <div className="grid md:grid-cols-2 gap-6">
      <div className="h-64 bg-gray-100 rounded-lg"></div>
      <div className="space-y-4">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
            <div className="flex items-center space-x-3">
              <div className="w-4 h-4 bg-gray-300 rounded-full"></div>
              <div className="h-4 bg-gray-300 rounded w-20"></div>
            </div>
            <div className="h-4 bg-gray-300 rounded w-24"></div>
          </div>
        ))}
      </div>
    </div>
  </div>
);

export const DenominationDistribution: React.FC<DenominationDistributionProps> = ({
  data,
  isLoading = false
}) => {
  const [viewMode, setViewMode] = useState<'pie' | 'bar'>('pie');

  if (isLoading) {
    return <LoadingComponent />;
  }

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <div className="flex items-center justify-center h-64 text-gray-500">
          <div className="text-center">
            <svg className="w-12 h-12 mx-auto mb-2 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 48 48">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-sm">No hay datos de denominaciones disponibles</p>
          </div>
        </div>
      </div>
    );
  }

  // Calcular totales
  const totalAmount = data.reduce((sum, item) => sum + item.amount, 0);
  const totalCount = data.reduce((sum, item) => sum + item.count, 0);

  // Preparar datos para el gráfico de barras
  const barData = data.map(item => ({
    ...item,
    amountInMillions: item.amount / 1000000
  }));

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">Distribución de Denominaciones</h3>
          <p className="text-sm text-gray-600">Composición del efectivo por tipo de billete</p>
        </div>
        
        {/* View toggles */}
        <div className="flex bg-gray-100 p-1 rounded-lg">
          <button
            onClick={() => setViewMode('pie')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              viewMode === 'pie' 
                ? 'bg-white text-blue-600 shadow-sm' 
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Circular
          </button>
          <button
            onClick={() => setViewMode('bar')}
            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
              viewMode === 'bar' 
                ? 'bg-white text-blue-600 shadow-sm' 
                : 'text-gray-600 hover:text-gray-800'
            }`}
          >
            Barras
          </button>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Chart */}
        <div className="h-64">
          {viewMode === 'pie' ? (
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={data}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={2}
                  dataKey="percentage"
                >
                  {data.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip content={<CustomTooltip />} />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={barData} layout="horizontal">
                <XAxis 
                  type="number" 
                  tick={{ fontSize: 12 }}
                  tickFormatter={(value) => `${value.toFixed(1)}M`}
                />
                <YAxis 
                  type="category" 
                  dataKey="denomination"
                  tick={{ fontSize: 12 }}
                  width={60}
                />
                <Tooltip 
                  formatter={(value: number) => [`$${(value * 1000000).toLocaleString('es-CO')}`, 'Valor']}
                  labelFormatter={(label) => `Denominación: ${label}`}
                />
                <Bar 
                  dataKey="amountInMillions" 
                  fill="#3b82f6"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Legend and details */}
        <div className="space-y-3">
          <div className="bg-gray-50 p-4 rounded-lg">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Resumen Total</h4>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Valor Total:</span>
                <span className="text-sm font-semibold">
                  ${new Intl.NumberFormat('es-CO').format(totalAmount)}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm text-gray-600">Billetes Totales:</span>
                <span className="text-sm font-semibold">
                  {new Intl.NumberFormat('es-CO').format(totalCount)}
                </span>
              </div>
            </div>
          </div>

          {/* Items list */}
          <div className="space-y-2">
            {data.map((item, index) => (
              <div 
                key={item.denomination}
                className="flex items-center justify-between p-3 bg-gray-50 hover:bg-gray-100 rounded-lg transition-colors"
              >
                <div className="flex items-center space-x-3">
                  <div 
                    className="w-4 h-4 rounded-full flex-shrink-0"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <div>
                    <p className="text-sm font-medium text-gray-900">{item.denomination}</p>
                    <p className="text-xs text-gray-500">
                      {new Intl.NumberFormat('es-CO').format(item.count)} billetes
                    </p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-gray-900">
                    {item.percentage}%
                  </p>
                  <p className="text-xs text-gray-500">
                    ${(item.amount / 1000000).toFixed(1)}M
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom insights */}
      <div className="mt-6 pt-4 border-t border-gray-100">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-blue-50 p-3 rounded-lg">
            <p className="text-xs text-blue-600 uppercase tracking-wider font-medium mb-1">
              Denominación Dominante
            </p>
            <p className="text-lg font-bold text-blue-900">
              {data.reduce((max, item) => item.percentage > max.percentage ? item : max).denomination}
            </p>
          </div>
          
          <div className="bg-green-50 p-3 rounded-lg">
            <p className="text-xs text-green-600 uppercase tracking-wider font-medium mb-1">
              Valor Promedio/Billete
            </p>
            <p className="text-lg font-bold text-green-900">
              ${Math.round(totalAmount / totalCount).toLocaleString('es-CO')}
            </p>
          </div>
          
          <div className="bg-purple-50 p-3 rounded-lg">
            <p className="text-xs text-purple-600 uppercase tracking-wider font-medium mb-1">
              Diversificación
            </p>
            <p className="text-lg font-bold text-purple-900">
              {data.length} tipos
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DenominationDistribution;