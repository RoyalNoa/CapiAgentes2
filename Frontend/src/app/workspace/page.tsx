"use client";

import dynamic from 'next/dynamic';

// Dynamically import WorkspaceTab to avoid SSR issues
const WorkspaceTab = dynamic(
  () => import('@/app/components/workspace/WorkspaceTab'),
  { 
    ssr: false,
    loading: () => (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white"></div>
      </div>
    )
  }
);

export default function WorkspacePage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      {/* Header */}
      <div className="bg-black/20 backdrop-blur-sm border-b border-white/20">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-white mb-2">
                🧠 AI Workspace
              </h1>
              <p className="text-gray-300">
                Espacio de trabajo inteligente con gestión de archivos, base de conocimiento y memoria persistente
              </p>
            </div>
            
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2 text-sm text-gray-400">
                <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                <span>Sistema activo</span>
              </div>
              
              <a
                href="/"
                className="px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors border border-white/20"
              >
                ← Volver al inicio
              </a>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 py-8">
        <div className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/20 overflow-hidden" style={{ height: 'calc(100vh - 200px)' }}>
          <WorkspaceTab />
        </div>
      </div>

      {/* Footer Info */}
      <div className="fixed bottom-4 right-4 bg-black/30 backdrop-blur-sm rounded-lg p-3 border border-white/20">
        <div className="flex items-center space-x-2 text-xs text-gray-300">
          <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
          <span>AI Workspace v1.0</span>
        </div>
      </div>
    </div>
  );
}