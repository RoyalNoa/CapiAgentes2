"use client";

import React, { useState } from 'react';
import {
  CubeTransparentIcon,
  MagnifyingGlassIcon,
  ClockIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import WorkspacePanel from './WorkspacePanel';
import KnowledgeSearch from './KnowledgeSearch';

type WorkspaceView = 'overview' | 'search' | 'tasks' | 'analytics';

export default function WorkspaceTab() {
  const [activeView, setActiveView] = useState<WorkspaceView>('overview');

  const views = [
    {
      key: 'overview' as const,
      label: 'Resumen',
      icon: CubeTransparentIcon,
      description: 'Vista general del workspace'
    },
    {
      key: 'search' as const,
      label: 'Buscar',
      icon: MagnifyingGlassIcon,
      description: 'Búsqueda en base de conocimiento'
    },
    {
      key: 'tasks' as const,
      label: 'Tareas',
      icon: ClockIcon,
      description: 'Gestor de tareas programadas'
    },
    {
      key: 'analytics' as const,
      label: 'Análisis',
      icon: ChartBarIcon,
      description: 'Estadísticas y métricas'
    }
  ];

  const renderContent = () => {
    switch (activeView) {
      case 'overview':
        return <WorkspacePanel />;
      case 'search':
        return <KnowledgeSearch />;
      case 'tasks':
        return (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <ClockIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-white mb-2">Gestor de Tareas</h3>
              <p className="text-gray-400">Próximamente: Gestión avanzada de tareas programadas</p>
            </div>
          </div>
        );
      case 'analytics':
        return (
          <div className="flex items-center justify-center h-full">
            <div className="text-center">
              <ChartBarIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <h3 className="text-xl font-medium text-white mb-2">Análisis Avanzado</h3>
              <p className="text-gray-400">Próximamente: Métricas detalladas y visualizaciones</p>
            </div>
          </div>
        );
      default:
        return <WorkspacePanel />;
    }
  };

  return (
    <div className="h-full flex flex-col bg-gray-900/50 backdrop-blur-sm">
      {/* Navigation */}
      <div className="flex border-b border-white/20 bg-white/5">
        {views.map(({ key, label, icon: Icon, description }) => (
          <button
            key={key}
            onClick={() => setActiveView(key)}
            className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium transition-colors relative group ${
              activeView === key
                ? 'text-blue-400 bg-blue-500/10 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
            title={description}
          >
            <Icon className="w-4 h-4" />
            <span className="hidden sm:block">{label}</span>
            
            {/* Tooltip for mobile */}
            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-2 py-1 bg-gray-800 text-white text-xs rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none sm:hidden">
              {description}
            </div>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {renderContent()}
      </div>
    </div>
  );
}