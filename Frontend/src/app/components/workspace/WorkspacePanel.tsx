"use client";

import React, { useState, useEffect } from 'react';
import { 
  FolderIcon, 
  DocumentTextIcon, 
  MagnifyingGlassIcon,
  ChartBarIcon,
  CpuChipIcon,
  ClockIcon,
  TrashIcon,
  EyeIcon,
  ArrowDownTrayIcon
} from '@heroicons/react/24/outline';

interface WorkspaceFile {
  name: string;
  path: string;
  size: number;
  created: string;
  modified: string;
  extension: string;
  metadata?: {
    created_by?: string;
    type?: string;
    file_id?: string;
  };
}

interface WorkspaceStats {
  total_files: number;
  total_size_mb: number;
  directories: Record<string, { count: number; size: number }>;
  file_types: Record<string, { count: number; size: number }>;
  last_activity: string;
}

interface MemoryStats {
  total_conversations: number;
  total_size_mb: number;
  period_stats: {
    last_day: number;
    last_week: number;
    last_month: number;
  };
}

interface KnowledgeStats {
  total_documents: number;
  total_keywords: number;
  document_types: Record<string, { count: number; avg_content_length: number }>;
  storage_info: {
    total_size_mb: number;
  };
}

interface TaskStats {
  total_tasks: number;
  running_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  status_breakdown: Record<string, number>;
  average_execution_time: number;
}

interface WorkspaceSummary {
  workspace_root: string;
  files: WorkspaceStats;
  knowledge_base: KnowledgeStats;
  memory: MemoryStats;
  last_updated: string;
}

const API_BASE = getApiBase();

export default function WorkspacePanel() {
  const [activeTab, setActiveTab] = useState<'files' | 'knowledge' | 'memory' | 'tasks'>('files');
  const [files, setFiles] = useState<WorkspaceFile[]>([]);
  const [summary, setSummary] = useState<WorkspaceSummary | null>(null);
  const [taskStats, setTaskStats] = useState<TaskStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedFile, setSelectedFile] = useState<WorkspaceFile | null>(null);

  useEffect(() => {
    fetchWorkspaceSummary();
    if (activeTab === 'files') {
      fetchFiles();
    } else if (activeTab === 'tasks') {
      fetchTaskStats();
    }
  }, [activeTab]);

  const fetchWorkspaceSummary = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/workspace/summary`);
      if (response.ok) {
        const data = await response.json();
        setSummary(data);
      }
    } catch (error) {
      console.error('Error fetching workspace summary:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchFiles = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/workspace/files?limit=100`);
      if (response.ok) {
        const data = await response.json();
        setFiles(data.files || []);
      }
    } catch (error) {
      console.error('Error fetching files:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTaskStats = async () => {
    try {
      setLoading(true);
      const response = await fetch(`${API_BASE}/api/workspace/tasks/scheduler/stats`);
      if (response.ok) {
        const data = await response.json();
        setTaskStats(data);
      }
    } catch (error) {
      console.error('Error fetching task stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const deleteFile = async (filePath: string) => {
    if (!confirm('¿Estás seguro de que deseas eliminar este archivo?')) {
      return;
    }

    try {
      const response = await fetch(`${API_BASE}/api/workspace/files/${encodeURIComponent(filePath)}`, {
        method: 'DELETE'
      });
      
      if (response.ok) {
        fetchFiles(); // Refresh file list
        setSelectedFile(null);
      } else {
        alert('Error al eliminar el archivo');
      }
    } catch (error) {
      console.error('Error deleting file:', error);
      alert('Error al eliminar el archivo');
    }
  };

  const filteredFiles = files.filter(file => 
    file.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    file.extension.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string): string => {
    return new Date(dateString).toLocaleString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getFileIcon = (extension: string) => {
    switch (extension.toLowerCase()) {
      case 'json':
      case 'yaml':
      case 'yml':
        return <DocumentTextIcon className="w-5 h-5 text-blue-500" />;
      case 'csv':
        return <ChartBarIcon className="w-5 h-5 text-green-500" />;
      case 'py':
      case 'js':
      case 'ts':
        return <CpuChipIcon className="w-5 h-5 text-purple-500" />;
      default:
        return <DocumentTextIcon className="w-5 h-5 text-gray-500" />;
    }
  };

  const renderOverviewTab = () => (
    <div className="space-y-6">
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
          <div className="flex items-center space-x-2">
            <FolderIcon className="w-6 h-6 text-blue-400" />
            <span className="text-sm text-gray-300">Archivos</span>
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {summary?.files.total_files || 0}
          </p>
          <p className="text-xs text-gray-400">
            {summary?.files.total_size_mb || 0} MB total
          </p>
        </div>

        <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
          <div className="flex items-center space-x-2">
            <DocumentTextIcon className="w-6 h-6 text-green-400" />
            <span className="text-sm text-gray-300">Documentos</span>
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {summary?.knowledge_base.total_documents || 0}
          </p>
          <p className="text-xs text-gray-400">
            {summary?.knowledge_base.total_keywords || 0} palabras clave
          </p>
        </div>

        <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
          <div className="flex items-center space-x-2">
            <CpuChipIcon className="w-6 h-6 text-purple-400" />
            <span className="text-sm text-gray-300">Conversaciones</span>
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {summary?.memory.total_conversations || 0}
          </p>
          <p className="text-xs text-gray-400">
            {summary?.memory.period_stats.last_week || 0} esta semana
          </p>
        </div>

        <div className="bg-white/10 backdrop-blur-md rounded-lg p-4 border border-white/20">
          <div className="flex items-center space-x-2">
            <ClockIcon className="w-6 h-6 text-yellow-400" />
            <span className="text-sm text-gray-300">Tareas</span>
          </div>
          <p className="text-2xl font-bold text-white mt-2">
            {taskStats?.total_tasks || 0}
          </p>
          <p className="text-xs text-gray-400">
            {taskStats?.completed_tasks || 0} completadas
          </p>
        </div>
      </div>

      {/* File Types Distribution */}
      <div className="bg-white/10 backdrop-blur-md rounded-lg p-6 border border-white/20">
        <h3 className="text-lg font-semibold text-white mb-4">Distribución por Tipo</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {Object.entries(summary?.files.file_types || {}).map(([type, stats]) => (
            <div key={type} className="text-center">
              <div className="bg-white/5 rounded-lg p-3">
                {getFileIcon(type)}
                <p className="text-sm font-medium text-white mt-2">.{type}</p>
                <p className="text-xs text-gray-400">{stats.count} archivos</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderFilesTab = () => (
    <div className="space-y-4">
      {/* Search */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Buscar archivos..."
          className="w-full pl-10 pr-4 py-2 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      {/* Files List */}
      <div className="bg-white/10 backdrop-blur-md rounded-lg border border-white/20 overflow-hidden">
        <div className="max-h-96 overflow-y-auto">
          {filteredFiles.length === 0 ? (
            <div className="p-8 text-center text-gray-400">
              {searchTerm ? 'No se encontraron archivos' : 'No hay archivos en el workspace'}
            </div>
          ) : (
            <div className="divide-y divide-white/10">
              {filteredFiles.map((file, index) => (
                <div 
                  key={index}
                  className="p-4 hover:bg-white/5 transition-colors cursor-pointer"
                  onClick={() => setSelectedFile(file)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      {getFileIcon(file.extension)}
                      <div>
                        <p className="text-sm font-medium text-white">{file.name}</p>
                        <p className="text-xs text-gray-400">
                          {formatFileSize(file.size)} • {formatDate(file.modified)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedFile(file);
                        }}
                        className="p-1 text-gray-400 hover:text-white transition-colors"
                        title="Ver detalles"
                      >
                        <EyeIcon className="w-4 h-4" />
                      </button>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteFile(file.path);
                        }}
                        className="p-1 text-gray-400 hover:text-red-400 transition-colors"
                        title="Eliminar"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );

  const tabConfig = [
    { key: 'files' as const, label: 'Archivos', icon: FolderIcon },
    { key: 'knowledge' as const, label: 'Base de Conocimiento', icon: DocumentTextIcon },
    { key: 'memory' as const, label: 'Memoria', icon: CpuChipIcon },
    { key: 'tasks' as const, label: 'Tareas', icon: ClockIcon },
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/20">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold text-white">AI Workspace</h2>
          <button
            onClick={fetchWorkspaceSummary}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
            disabled={loading}
          >
            {loading ? 'Actualizando...' : 'Actualizar'}
          </button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-white/20">
        {tabConfig.map(({ key, label, icon: Icon }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            className={`flex items-center space-x-2 px-4 py-3 text-sm font-medium transition-colors ${
              activeTab === key
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            <Icon className="w-4 h-4" />
            <span className="hidden sm:block">{label}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 p-4 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          </div>
        ) : (
          <>
            {activeTab === 'files' && renderFilesTab()}
            {activeTab === 'knowledge' && renderOverviewTab()}
            {activeTab === 'memory' && renderOverviewTab()}
            {activeTab === 'tasks' && renderOverviewTab()}
          </>
        )}
      </div>

      {/* File Details Modal */}
      {selectedFile && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900/95 rounded-lg border border-white/20 max-w-lg w-full max-h-96 overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white">Detalles del Archivo</h3>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-center space-x-3">
                  {getFileIcon(selectedFile.extension)}
                  <span className="text-white font-medium">{selectedFile.name}</span>
                </div>
                
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Tamaño:</span>
                    <p className="text-white">{formatFileSize(selectedFile.size)}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Tipo:</span>
                    <p className="text-white">.{selectedFile.extension}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Creado:</span>
                    <p className="text-white">{formatDate(selectedFile.created)}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Modificado:</span>
                    <p className="text-white">{formatDate(selectedFile.modified)}</p>
                  </div>
                </div>
                
                <div>
                  <span className="text-gray-400">Ruta:</span>
                  <p className="text-white text-sm break-all">{selectedFile.path}</p>
                </div>
                
                {selectedFile.metadata && (
                  <div>
                    <span className="text-gray-400">Metadata:</span>
                    <div className="bg-black/30 rounded p-2 mt-1">
                      <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                        {JSON.stringify(selectedFile.metadata, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="flex justify-end space-x-2 mt-6">
                <button
                  onClick={() => deleteFile(selectedFile.path)}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white text-sm rounded-lg transition-colors"
                >
                  Eliminar
                </button>
                <button
                  onClick={() => setSelectedFile(null)}
                  className="px-4 py-2 bg-gray-600 hover:bg-gray-700 text-white text-sm rounded-lg transition-colors"
                >
                  Cerrar
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}