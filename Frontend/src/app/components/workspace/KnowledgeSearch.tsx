"use client";

import React, { useState, useEffect } from 'react';
import { getApiBase } from '@/app/utils/orchestrator/client';
import { 
  MagnifyingGlassIcon,
  DocumentTextIcon,
  SparklesIcon,
  CalendarIcon,
  TagIcon,
  XMarkIcon
} from '@heroicons/react/24/outline';

interface SearchResult {
  doc_id: string;
  title: string;
  content: string;
  score: number;
  created_at: string;
  updated_at: string;
  doc_type: string;
  file_path?: string;
  metadata: Record<string, any>;
  relevant_snippets: string[];
}

interface SearchResponse {
  results: SearchResult[];
  total: number;
}

const API_BASE = getApiBase();

export default function KnowledgeSearch() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<SearchResult | null>(null);
  const [docType, setDocType] = useState<string>('');
  const [daysBack, setDaysBack] = useState<number | undefined>();
  const [hasSearched, setHasSearched] = useState(false);

  const searchDocuments = async () => {
    if (!query.trim()) return;

    try {
      setLoading(true);
      setHasSearched(true);
      
      const params = new URLSearchParams({
        query: query.trim(),
        limit: '20'
      });
      
      if (docType) params.append('doc_type', docType);
      if (daysBack) params.append('days_back', daysBack.toString());

      const response = await fetch(`${API_BASE}/api/workspace/knowledge/search?${params}`);
      
      if (response.ok) {
        const data: SearchResponse = await response.json();
        setResults(data.results);
      } else {
        setResults([]);
      }
    } catch (error) {
      console.error('Error searching knowledge base:', error);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      searchDocuments();
    }
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

  const highlightText = (text: string, query: string): React.ReactNode => {
    if (!query) return text;
    
    const parts = text.split(new RegExp(`(${query})`, 'gi'));
    return parts.map((part, index) => 
      part.toLowerCase() === query.toLowerCase() ? (
        <mark key={index} className="bg-yellow-400/30 text-yellow-200 rounded px-1">
          {part}
        </mark>
      ) : part
    );
  };

  const getDocTypeIcon = (docType: string) => {
    switch (docType.toLowerCase()) {
      case 'analysis':
        return <SparklesIcon className="w-4 h-4 text-blue-400" />;
      case 'general':
        return <DocumentTextIcon className="w-4 h-4 text-gray-400" />;
      default:
        return <TagIcon className="w-4 h-4 text-purple-400" />;
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 50) return 'text-green-400';
    if (score >= 20) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="h-full flex flex-col">
      {/* Search Header */}
      <div className="p-4 border-b border-white/20">
        <div className="flex items-center space-x-2">
          <SparklesIcon className="w-6 h-6 text-blue-400" />
          <h2 className="text-xl font-semibold text-white">Búsqueda en Base de Conocimiento</h2>
        </div>
      </div>

      {/* Search Controls */}
      <div className="p-4 space-y-4 border-b border-white/20">
        {/* Main Search */}
        <div className="relative">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
          <input
            type="text"
            placeholder="Buscar en documentos y análisis anteriores..."
            className="w-full pl-10 pr-12 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyPress={handleKeyPress}
          />
          <button
            onClick={searchDocuments}
            disabled={loading || !query.trim()}
            className="absolute right-2 top-1/2 transform -translate-y-1/2 p-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded-lg transition-colors"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <MagnifyingGlassIcon className="w-4 h-4 text-white" />
            )}
          </button>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-3">
          <select
            value={docType}
            onChange={(e) => setDocType(e.target.value)}
            className="px-3 py-1 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todos los tipos</option>
            <option value="analysis">Análisis</option>
            <option value="general">General</option>
          </select>

          <select
            value={daysBack || ''}
            onChange={(e) => setDaysBack(e.target.value ? parseInt(e.target.value) : undefined)}
            className="px-3 py-1 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">Todo el tiempo</option>
            <option value="7">Última semana</option>
            <option value="30">Último mes</option>
            <option value="90">Últimos 3 meses</option>
          </select>
          
          {(docType || daysBack) && (
            <button
              onClick={() => {
                setDocType('');
                setDaysBack(undefined);
                if (hasSearched) searchDocuments();
              }}
              className="px-2 py-1 text-xs text-gray-400 hover:text-white transition-colors"
            >
              Limpiar filtros
            </button>
          )}
        </div>
      </div>

      {/* Results */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center h-32">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-400"></div>
          </div>
        ) : hasSearched ? (
          <div className="p-4">
            {results.length === 0 ? (
              <div className="text-center py-8">
                <MagnifyingGlassIcon className="w-12 h-12 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400 text-lg">No se encontraron documentos</p>
                <p className="text-gray-500 text-sm">Intenta con términos diferentes o ajusta los filtros</p>
              </div>
            ) : (
              <>
                <div className="mb-4">
                  <p className="text-sm text-gray-400">
                    Se encontraron {results.length} documentos para &ldquo;{query}&rdquo;
                  </p>
                </div>
                
                <div className="space-y-4">
                  {results.map((result) => (
                    <div
                      key={result.doc_id}
                      className="bg-white/5 backdrop-blur-sm rounded-lg border border-white/10 p-4 hover:bg-white/10 transition-colors cursor-pointer"
                      onClick={() => setSelectedDocument(result)}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center space-x-2">
                          {getDocTypeIcon(result.doc_type)}
                          <h3 className="text-white font-medium">
                            {highlightText(result.title, query)}
                          </h3>
                          <span className={`text-xs px-2 py-1 rounded ${getScoreColor(result.score)}`}>
                            Score: {result.score}
                          </span>
                        </div>
                        <span className="text-xs text-gray-500 capitalize">
                          {result.doc_type}
                        </span>
                      </div>

                      {/* Relevant Snippets */}
                      {result.relevant_snippets.length > 0 && (
                        <div className="mb-3">
                          {result.relevant_snippets.slice(0, 2).map((snippet, index) => (
                            <p key={index} className="text-sm text-gray-300 mb-1">
                              &ldquo;{highlightText(snippet, query)}&rdquo;
                            </p>
                          ))}
                        </div>
                      )}

                      <div className="flex items-center justify-between text-xs text-gray-500">
                        <div className="flex items-center space-x-4">
                          <span className="flex items-center space-x-1">
                            <CalendarIcon className="w-3 h-3" />
                            <span>{formatDate(result.updated_at)}</span>
                          </span>
                          {result.file_path && (
                            <span className="truncate max-w-xs">
                              📁 {result.file_path}
                            </span>
                          )}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedDocument(result);
                          }}
                          className="text-blue-400 hover:text-blue-300 transition-colors"
                        >
                          Ver detalles →
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <SparklesIcon className="w-16 h-16 text-gray-600 mb-4" />
            <h3 className="text-xl font-medium text-white mb-2">Base de Conocimiento</h3>
            <p className="text-gray-400 max-w-md">
              Busca en todos los análisis, documentos y datos generados previamente. 
              La IA puede encontrar información relevante de trabajos anteriores.
            </p>
          </div>
        )}
      </div>

      {/* Document Details Modal */}
      {selectedDocument && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-gray-900/95 rounded-lg border border-white/20 max-w-4xl w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center space-x-3">
                  {getDocTypeIcon(selectedDocument.doc_type)}
                  <h3 className="text-lg font-semibold text-white">
                    {selectedDocument.title}
                  </h3>
                  <span className="px-2 py-1 bg-blue-600/20 text-blue-400 text-xs rounded">
                    {selectedDocument.doc_type}
                  </span>
                </div>
                <button
                  onClick={() => setSelectedDocument(null)}
                  className="text-gray-400 hover:text-white"
                >
                  <XMarkIcon className="w-6 h-6" />
                </button>
              </div>
              
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Score de relevancia:</span>
                    <p className={`font-medium ${getScoreColor(selectedDocument.score)}`}>
                      {selectedDocument.score}
                    </p>
                  </div>
                  <div>
                    <span className="text-gray-400">ID del documento:</span>
                    <p className="text-white font-mono text-xs">{selectedDocument.doc_id}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Creado:</span>
                    <p className="text-white">{formatDate(selectedDocument.created_at)}</p>
                  </div>
                  <div>
                    <span className="text-gray-400">Actualizado:</span>
                    <p className="text-white">{formatDate(selectedDocument.updated_at)}</p>
                  </div>
                </div>
                
                {selectedDocument.file_path && (
                  <div>
                    <span className="text-gray-400">Archivo asociado:</span>
                    <p className="text-white text-sm break-all">{selectedDocument.file_path}</p>
                  </div>
                )}

                {/* Relevant Snippets */}
                {selectedDocument.relevant_snippets.length > 0 && (
                  <div>
                    <span className="text-gray-400">Fragmentos relevantes:</span>
                    <div className="space-y-2 mt-2">
                      {selectedDocument.relevant_snippets.map((snippet, index) => (
                        <div key={index} className="bg-black/30 rounded p-3">
                          <p className="text-sm text-gray-200">
                            &ldquo;{highlightText(snippet, query)}&rdquo;
                          </p>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                
                {/* Full Content */}
                <div>
                  <span className="text-gray-400">Contenido completo:</span>
                  <div className="bg-black/30 rounded p-4 mt-2 max-h-64 overflow-y-auto">
                    <pre className="text-sm text-gray-300 whitespace-pre-wrap">
                      {highlightText(selectedDocument.content, query)}
                    </pre>
                  </div>
                </div>
                
                {/* Metadata */}
                {Object.keys(selectedDocument.metadata).length > 0 && (
                  <div>
                    <span className="text-gray-400">Metadata:</span>
                    <div className="bg-black/30 rounded p-3 mt-2">
                      <pre className="text-xs text-gray-300 whitespace-pre-wrap">
                        {JSON.stringify(selectedDocument.metadata, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
              </div>
              
              <div className="flex justify-end space-x-2 mt-6">
                <button
                  onClick={() => setSelectedDocument(null)}
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
