'use client';

import React, {
  MouseEvent as ReactMouseEvent,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  ArrowPathIcon,
  ChevronDownIcon,
  ChevronRightIcon,
  DocumentTextIcon,
  FolderIcon,
  TrashIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';
import { API_BASE } from '@/app/utils/orchestrator/client';

interface TreeNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  modified_at: string;
  size_bytes?: number;
  has_children?: boolean;
  children?: TreeNode[];
  expanded?: boolean;
  loading?: boolean;
}

interface SelectedMeta {
  size_bytes?: number;
  modified_at?: string;
}

type FeedbackTone = 'success' | 'error' | null;

const MOUSE_MARGIN = 16;

const HUD_COLORS = {
  overlay: 'rgba(4, 12, 24, 0.72)',
  panelGradient: 'linear-gradient(135deg, rgba(0, 12, 28, 0.96), rgba(0, 28, 54, 0.9))',
  panelSoft: 'linear-gradient(135deg, rgba(0, 18, 38, 0.85), rgba(0, 34, 64, 0.82))',
  border: 'rgba(0, 229, 255, 0.25)',
  borderSoft: 'rgba(0, 229, 255, 0.18)',
  textPrimary: '#e6f1ff',
  textMuted: '#8aa0c5',
  accent: '#00e5ff',
  accentSoft: '#7df9ff',
  danger: '#f97373',
} as const;

const CONTAINER_STYLE: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  zIndex: 40,
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  backgroundColor: HUD_COLORS.overlay,
  padding: 16,
};

const PANEL_BASE_STYLE: React.CSSProperties = {
  position: 'absolute',
  display: 'flex',
  flexDirection: 'column',
  width: '100%',
  maxWidth: 960,
  minWidth: 360,
  maxHeight: '80vh',
  background: HUD_COLORS.panelGradient,
  color: HUD_COLORS.textPrimary,
  borderRadius: 16,
  border: `1px solid ${HUD_COLORS.border}`,
  boxShadow: '0 28px 50px rgba(0, 12, 28, 0.55)',
  overflow: 'visible',
  userSelect: 'none',
};

const HEADER_STYLE: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: 12,
  padding: '18px 24px',
  cursor: 'grab',
  background: 'linear-gradient(135deg, rgba(0, 32, 64, 0.9), rgba(0, 20, 48, 0.85))',
  borderBottom: `1px solid ${HUD_COLORS.borderSoft}`,
};

const TITLE_STYLE: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 12,
  fontSize: 18,
  fontWeight: 600,
};

const ACTIONS_STYLE: React.CSSProperties = {
  display: 'flex',
  gap: 8,
  alignItems: 'center',
};

const BODY_STYLE: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  gap: 16,
  padding: 16,
  userSelect: 'text',
  minHeight: 0,
};

const SIDEBAR_STYLE: React.CSSProperties = {
  flex: '0 0 30%',
  minWidth: 240,
  maxWidth: 320,
  background: HUD_COLORS.panelSoft,
  borderRadius: 12,
  border: `1px solid ${HUD_COLORS.borderSoft}`,
  padding: 16,
  display: 'flex',
  flexDirection: 'column',
  gap: 12,
  overflowY: 'auto',
  minHeight: 0,
};

const PANEL_STYLE: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  background: 'linear-gradient(135deg, rgba(0, 16, 32, 0.92), rgba(0, 34, 60, 0.88))',
  borderRadius: 12,
  border: `1px solid ${HUD_COLORS.borderSoft}`,
  padding: 16,
  gap: 12,
  overflow: 'hidden',
};

const FILE_CONTENT_STYLE: React.CSSProperties = {
  flex: 1,
  background: 'linear-gradient(135deg, rgba(0, 18, 36, 0.9), rgba(0, 28, 50, 0.88))',
  borderRadius: 12,
  border: `1px solid ${HUD_COLORS.borderSoft}`,
  padding: 16,
  overflowY: 'auto',
  fontFamily:
    'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
  fontSize: 13,
  lineHeight: 1.55,
  whiteSpace: 'pre-wrap',
  wordBreak: 'break-word',
  color: HUD_COLORS.textPrimary,
};

const EMPTY_STATE_STYLE: React.CSSProperties = {
  flex: 1,
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 12,
  color: HUD_COLORS.textMuted,
};

const TREE_ITEM_STYLE: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  gap: 8,
  padding: '6px 8px',
  borderRadius: 8,
  border: '1px solid transparent',
  background: 'transparent',
  cursor: 'pointer',
  color: HUD_COLORS.textPrimary,
  transition: 'background-color 0.2s ease, color 0.2s ease, border-color 0.2s ease',
};

const TREE_ITEM_ACTIVE_STYLE: React.CSSProperties = {
  backgroundColor: 'rgba(0, 229, 255, 0.12)',
  borderColor: HUD_COLORS.border,
  color: HUD_COLORS.textPrimary,
  boxShadow: `0 0 12px ${HUD_COLORS.accent}2a`,
};

const BUTTON_BASE_STYLE: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  borderRadius: 10,
  border: '1px solid transparent',
  padding: '6px 14px',
  fontSize: 13,
  fontWeight: 500,
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  backgroundColor: 'rgba(0, 229, 255, 0.12)',
  color: HUD_COLORS.textPrimary,
  outline: 'none',
};

const BUTTON_DESTRUCTIVE_STYLE: React.CSSProperties = {
  backgroundColor: 'rgba(239, 68, 68, 0.12)',
  color: HUD_COLORS.danger,
  borderColor: 'rgba(248, 113, 113, 0.35)',
};

const formatBytes = (value?: number) => {
  if (value === undefined) return '—';
  if (value === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const exponent = Math.min(units.length - 1, Math.floor(Math.log(value) / Math.log(1024)));
  const size = value / 1024 ** exponent;
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[exponent]}`;
};

const normalizeEntries = (items: any[] | undefined | null): TreeNode[] => {
  if (!Array.isArray(items)) {
    return [];
  }
  return items
    .map((entry) => {
      if (!entry || typeof entry !== 'object') {
        return null;
      }
      const node: TreeNode = {
        name: String(entry.name ?? ''),
        path: String(entry.path ?? ''),
        type: entry.type === 'directory' ? 'directory' : 'file',
        modified_at: String(entry.modified_at ?? new Date().toISOString()),
        size_bytes:
          typeof entry.size_bytes === 'number' ? entry.size_bytes : undefined,
        has_children: Boolean(entry.has_children),
        expanded: false,
      };
      if (Array.isArray(entry.children) && entry.children.length > 0) {
        node.children = normalizeEntries(entry.children);
        node.has_children = node.children.length > 0;
      }
      return node;
    })
    .filter((node): node is TreeNode => Boolean(node && node.name));
};

const updateTreeNode = (
  nodes: TreeNode[],
  targetPath: string,
  updater: (node: TreeNode) => TreeNode,
): TreeNode[] => {
  let changed = false;

  const nextNodes = nodes.map((node) => {
    if (node.path === targetPath) {
      changed = true;
      return updater(node);
    }
    if (node.children) {
      const updatedChildren = updateTreeNode(node.children, targetPath, updater);
      if (updatedChildren !== node.children) {
        changed = true;
        return { ...node, children: updatedChildren };
      }
    }
    return node;
  });

  return changed ? nextNodes : nodes;
};

const findTreeNode = (nodes: TreeNode[], targetPath: string): TreeNode | undefined => {
  for (const node of nodes) {
    if (node.path === targetPath) {
      return node;
    }
    if (node.children) {
      const found = findTreeNode(node.children, targetPath);
      if (found) {
        return found;
      }
    }
  }
  return undefined;
};

const getParentPath = (path: string): string => {
  if (!path) {
    return '';
  }
  const segments = path.split('/');
  segments.pop();
  return segments.join('/');
};

const SessionFilesViewer: React.FC<{ onClose: () => void }> = ({ onClose }) => {
  const [entries, setEntries] = useState<TreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [selectedMeta, setSelectedMeta] = useState<SelectedMeta>({});
  const [fileContent, setFileContent] = useState<string>('');
  const [treeError, setTreeError] = useState<string | null>(null);
  const [fileError, setFileError] = useState<string | null>(null);
  const [isTreeLoading, setIsTreeLoading] = useState<boolean>(false);
  const [isFileLoading, setIsFileLoading] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<FeedbackTone>(null);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [panelPosition, setPanelPosition] = useState<{ x: number; y: number } | null>(null);

  const panelRef = useRef<HTMLDivElement | null>(null);
  const dragOffsetRef = useRef<{ offsetX: number; offsetY: number }>({ offsetX: 0, offsetY: 0 });

  const clampPosition = useCallback((pos: { x: number; y: number }) => {
    const panelNode = panelRef.current;
    if (!panelNode) return pos;
    const { offsetWidth, offsetHeight } = panelNode;
    const maxX = Math.max(MOUSE_MARGIN, window.innerWidth - offsetWidth - MOUSE_MARGIN);
    const maxY = Math.max(MOUSE_MARGIN, window.innerHeight - offsetHeight - MOUSE_MARGIN);
    return {
      x: Math.min(Math.max(MOUSE_MARGIN, pos.x), maxX),
      y: Math.min(Math.max(MOUSE_MARGIN, pos.y), maxY),
    };
  }, []);

  const initializePosition = useCallback(() => {
    const panelNode = panelRef.current;
    if (!panelNode) return;
    setPanelPosition((current) => {
      if (current) {
        return clampPosition(current);
      }
      const rect = panelNode.getBoundingClientRect();
      return clampPosition({
        x: (window.innerWidth - rect.width) / 2,
        y: (window.innerHeight - rect.height) / 2,
      });
    });
  }, [clampPosition]);

  useEffect(() => {
    initializePosition();
  }, [initializePosition]);

  useEffect(() => {
    const handleResize = () => initializePosition();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [initializePosition]);

  const loadDirectory = useCallback(async (targetPath?: string | null) => {
    const query = targetPath ? `?path=${encodeURIComponent(targetPath)}` : '';
    const response = await fetch(`${API_BASE}/api/session-files/tree${query}`);
    if (!response.ok) {
      throw new Error(`Error ${response.status} al cargar ${targetPath ?? 'el directorio raíz'}.`);
    }
    const data = await response.json();
    return normalizeEntries(data?.entries);
  }, []);

  const fetchTree = useCallback(async () => {
    setIsTreeLoading(true);
    setTreeError(null);
    setFeedbackMessage(null);
    setFeedbackTone(null);
    try {
      const rootEntries = await loadDirectory(null);
      setEntries(rootEntries);
    } catch (error) {
      console.error('Error fetching session files tree', error);
      setTreeError('No pudimos cargar la estructura de archivos. Intenta recargar.');
      setEntries([]);
    } finally {
      setIsTreeLoading(false);
    }
  }, [loadDirectory]);

  const refreshDirectory = useCallback(
    async (targetPath?: string | null) => {
      try {
        setTreeError(null);
        setFeedbackMessage(null);
        setFeedbackTone(null);
        const children = await loadDirectory(targetPath ?? null);
        if (!targetPath) {
          setEntries(children);
          return;
        }
        setEntries((prev) =>
          updateTreeNode(prev, targetPath, (node) => ({
            ...node,
            children,
            expanded: true,
            loading: false,
            has_children: children.length > 0,
          })),
        );
      } catch (error) {
        console.error('Error refreshing directory view', error);
        setFeedbackMessage('No se pudo actualizar la carpeta seleccionada.');
        setFeedbackTone('error');
      }
    },
    [loadDirectory],
  );

  useEffect(() => {
    fetchTree().catch((error) => {
      console.error('Unexpected tree fetch failure', error);
    });
  }, [fetchTree]);

  const fetchFile = useCallback(async (entry: TreeNode) => {
    if (entry.type === 'directory') return;
    setSelectedPath(entry.path);
    setSelectedMeta({ size_bytes: entry.size_bytes, modified_at: entry.modified_at });
    setFileError(null);
    setFeedbackMessage(null);
    setFeedbackTone(null);
    setIsFileLoading(true);
    try {
      const response = await fetch(
        `${API_BASE}/api/session-files/file?path=${encodeURIComponent(entry.path)}`,
      );
      if (!response.ok) {
        throw new Error(`Error ${response.status} al obtener el archivo.`);
      }
      const payload = await response.json();
      setFileContent(payload?.content ?? '');
      setSelectedMeta({ size_bytes: payload?.size_bytes, modified_at: payload?.modified_at });
    } catch (error) {
      console.error('Error fetching session file', error);
      setFileError('No se pudo cargar el archivo seleccionado. Verifica que siga existiendo.');
      setFileContent('');
    } finally {
      setIsFileLoading(false);
    }
  }, []);

  const handleDelete = useCallback(async () => {
    if (!selectedPath) return;
    const confirmed = window.confirm(`¿Eliminar definitivamente "${selectedPath}"?`);
    if (!confirmed) return;

    setIsDeleting(true);
    setFeedbackMessage(null);
    setFeedbackTone(null);
    setTreeError(null);
    try {
      const response = await fetch(`${API_BASE}/api/session-files/file`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: selectedPath }),
      });
      if (!response.ok) {
        throw new Error(`Error ${response.status} al eliminar el archivo.`);
      }
      setSelectedPath(null);
      setFileContent('');
      setSelectedMeta({});
      setFeedbackMessage('Archivo eliminado correctamente.');
      setFeedbackTone('success');
      const parentPath = getParentPath(selectedPath);
      await refreshDirectory(parentPath || null);
    } catch (error) {
      console.error('Error deleting session file', error);
      setFeedbackMessage('No se pudo eliminar el archivo. Intenta nuevamente.');
      setFeedbackTone('error');
    } finally {
      setIsDeleting(false);
    }
  }, [refreshDirectory, selectedPath]);

  const handleToggleDirectory = useCallback(
    async (path: string) => {
      const snapshot = findTreeNode(entries, path);
      if (!snapshot) {
        return;
      }

      if (snapshot.expanded) {
        setEntries((prev) => updateTreeNode(prev, path, (node) => ({ ...node, expanded: false })));
        return;
      }

      if (!snapshot.has_children && !snapshot.children?.length) {
        setEntries((prev) =>
          updateTreeNode(prev, path, (node) => ({ ...node, expanded: true, children: [] })),
        );
        return;
      }

      if (snapshot.children && snapshot.children.length > 0) {
        setEntries((prev) => updateTreeNode(prev, path, (node) => ({ ...node, expanded: true })));
        return;
      }

      setEntries((prev) =>
        updateTreeNode(prev, path, (node) => ({ ...node, expanded: true, loading: true })),
      );

      try {
        const children = await loadDirectory(path);
        setEntries((prev) =>
          updateTreeNode(prev, path, (node) => ({
            ...node,
            children,
            loading: false,
            expanded: true,
            has_children: children.length > 0,
          })),
        );
      } catch (error) {
        console.error('Error fetching directory contents', error);
        setFeedbackMessage('No se pudo cargar la carpeta seleccionada.');
        setFeedbackTone('error');
        setEntries((prev) =>
          updateTreeNode(prev, path, (node) => ({ ...node, loading: false, expanded: false })),
        );
      }
    },
    [entries, loadDirectory],
  );

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (event: globalThis.MouseEvent) => {
      setPanelPosition((current) => {
        if (!panelRef.current || current === null) return current;
        const nextPosition = {
          x: event.clientX - dragOffsetRef.current.offsetX,
          y: event.clientY - dragOffsetRef.current.offsetY,
        };
        return clampPosition(nextPosition);
      });
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);

    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, [clampPosition, isDragging]);

  const handleHeaderMouseDown = (event: ReactMouseEvent<HTMLDivElement>) => {
    const panelNode = panelRef.current;
    if (!panelNode) return;
    const rect = panelNode.getBoundingClientRect();
    dragOffsetRef.current = {
      offsetX: event.clientX - rect.left,
      offsetY: event.clientY - rect.top,
    };
    setIsDragging(true);
  };

  const renderTree = useCallback(
    (items: TreeNode[], depth = 0): React.ReactNode => (
      <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
        {items.map((entry) => {
          const isDirectory = entry.type === 'directory';
          const isExpanded = Boolean(entry.expanded);
          const isSelected = !isDirectory && selectedPath === entry.path;
          const indentation = depth * 14;

          return (
            <li key={entry.path} style={{ marginBottom: 4 }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <button
                  type="button"
                  onClick={() => {
                    if (isDirectory) {
                      void handleToggleDirectory(entry.path);
                    } else {
                      void fetchFile(entry);
                    }
                  }}
                  style={{
                    ...TREE_ITEM_STYLE,
                    ...(isSelected ? TREE_ITEM_ACTIVE_STYLE : {}),
                    justifyContent: 'flex-start',
                    paddingLeft: `${isDirectory ? 6 + indentation : 24 + indentation}px`,
                    paddingRight: 10,
                    opacity: isDirectory ? 0.92 : 1,
                    gap: 10,
                  }}
                >
                  {isDirectory ? (
                    <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: 14 }}>
                      {isExpanded ? (
                        <ChevronDownIcon width={14} height={14} aria-hidden />
                      ) : (
                        <ChevronRightIcon width={14} height={14} aria-hidden />
                      )}
                    </span>
                  ) : (
                    <span style={{ width: 14 }} />
                  )}
                  {isDirectory ? (
                    <FolderIcon style={{ width: 16, height: 16 }} aria-hidden />
                  ) : (
                    <DocumentTextIcon style={{ width: 16, height: 16 }} aria-hidden />
                  )}
                  <span style={{ flex: 1, textAlign: 'left' }}>{entry.name}</span>
                  {isDirectory ? (
                    entry.loading ? (
                      <ArrowPathIcon
                        style={{ width: 14, height: 14, animation: 'spin 1s linear infinite' }}
                        aria-hidden
                      />
                    ) : null
                  ) : (
                    <span style={{ fontSize: 11, color: HUD_COLORS.textMuted }}>{formatBytes(entry.size_bytes)}</span>
                  )}
                </button>
                {isDirectory && isExpanded && entry.loading && (
                  <span style={{ fontSize: 11, color: HUD_COLORS.textMuted, paddingLeft: `${32 + indentation}px` }}>
                    Cargando…
                  </span>
                )}
              </div>
              {isDirectory && isExpanded && !entry.loading && entry.children && entry.children.length > 0 && (
                <div style={{ marginLeft: 20 }}>{renderTree(entry.children, depth + 1)}</div>
              )}
              {isDirectory && isExpanded && !entry.loading && (!entry.children || entry.children.length === 0) && (
                <div
                  style={{
                    marginLeft: `${32 + indentation}px`,
                    fontSize: 11,
                    color: HUD_COLORS.textMuted,
                  }}
                >
                  Carpeta vacía
                </div>
              )}
            </li>
          );
        })}
      </ul>
    ),
    [fetchFile, handleToggleDirectory, selectedPath],
  );

  const panelDynamicStyle = useMemo<React.CSSProperties>(() => {
    if (!panelPosition) {
      return {
        ...PANEL_BASE_STYLE,
        cursor: isDragging ? 'grabbing' : 'grab',
      };
    }
    return {
      ...PANEL_BASE_STYLE,
      left: panelPosition.x,
      top: panelPosition.y,
      cursor: isDragging ? 'grabbing' : 'grab',
    };
  }, [isDragging, panelPosition]);

  const deleteDisabled = !selectedPath || isDeleting || isTreeLoading;
  const reloadDisabled = isTreeLoading || isDeleting;

  return (
    <div style={CONTAINER_STYLE}>
      <div ref={panelRef} style={panelDynamicStyle}>
        <div
          style={{
            ...HEADER_STYLE,
            cursor: isDragging ? 'grabbing' : 'grab',
          }}
          onMouseDown={handleHeaderMouseDown}
        >
          <div style={TITLE_STYLE}>
            <FolderIcon style={{ width: 22, height: 22 }} aria-hidden />
            <div>
              <div>Archivos de la sesión</div>
              <div style={{ fontSize: 12, color: '#94a3b8', fontWeight: 400 }}>
                Explora `ia_workspace/data` y gestiona tus archivos recientes
              </div>
            </div>
          </div>
          <div style={ACTIONS_STYLE}>
            <button
              style={{
                ...BUTTON_BASE_STYLE,
                backgroundColor: 'rgba(59, 130, 246, 0.12)',
                borderColor: 'rgba(59, 130, 246, 0.35)',
                opacity: reloadDisabled ? 0.65 : 1,
                pointerEvents: reloadDisabled ? 'none' : 'auto',
              }}
              onMouseDown={(event) => event.stopPropagation()}
              onClick={() => void fetchTree()}
              disabled={reloadDisabled}
            >
              <ArrowPathIcon style={{ width: 16, height: 16 }} aria-hidden />
              Recargar
            </button>
            <button
              style={{
                ...BUTTON_BASE_STYLE,
                ...BUTTON_DESTRUCTIVE_STYLE,
                opacity: deleteDisabled ? 0.45 : 1,
                pointerEvents: deleteDisabled ? 'none' : 'auto',
              }}
              onMouseDown={(event) => event.stopPropagation()}
              onClick={() => void handleDelete()}
              disabled={deleteDisabled}
            >
              <TrashIcon style={{ width: 16, height: 16 }} aria-hidden />
              Eliminar
            </button>
            <button
              style={{
                ...BUTTON_BASE_STYLE,
                backgroundColor: 'rgba(15, 23, 42, 0.55)',
                color: '#cbd5f5',
                borderColor: 'rgba(148, 163, 184, 0.25)',
              }}
              onMouseDown={(event) => event.stopPropagation()}
              onClick={onClose}
            >
              <XMarkIcon style={{ width: 18, height: 18 }} aria-hidden />
            </button>
          </div>
        </div>

        <div style={BODY_STYLE}>
          <aside style={SIDEBAR_STYLE}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
              <span style={{ fontSize: 13, fontWeight: 600, color: '#cbd5f5' }}>Estructura</span>
              {(isTreeLoading || isDeleting) && (
                <span style={{ fontSize: 11, color: '#94a3b8' }}>Actualizando…</span>
              )}
            </div>
            {treeError ? (
              <div style={{ fontSize: 12, color: '#fca5a5' }}>{treeError}</div>
            ) : entries.length > 0 ? (
              <div style={{ flex: 1, overflowY: 'auto', paddingRight: 4 }}>
                {renderTree(entries)}
              </div>
            ) : (
              <div style={{ fontSize: 12, color: '#94a3b8' }}>
                No se encontraron archivos en esta sesión.
              </div>
            )}
          </aside>

          <section style={PANEL_STYLE}>
            <header style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 style={{ fontSize: 15, fontWeight: 600, margin: 0 }}>Vista previa</h2>
                {selectedPath && (
                  <span style={{ fontSize: 12, color: '#94a3b8', maxWidth: '60%', textOverflow: 'ellipsis', whiteSpace: 'nowrap', overflow: 'hidden' }}>
                    {selectedPath}
                  </span>
                )}
              </div>
              {selectedPath && (
                <dl style={{ display: 'flex', gap: 16, fontSize: 12, color: '#94a3b8', margin: 0 }}>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <dt style={{ fontWeight: 500 }}>Peso:</dt>
                    <dd style={{ margin: 0 }}>{formatBytes(selectedMeta.size_bytes)}</dd>
                  </div>
                  {selectedMeta.modified_at && (
                    <div style={{ display: 'flex', gap: 6 }}>
                      <dt style={{ fontWeight: 500 }}>Modificado:</dt>
                      <dd style={{ margin: 0 }}>
                        {new Date(selectedMeta.modified_at).toLocaleString()}
                      </dd>
                    </div>
                  )}
                </dl>
              )}
            </header>

            {feedbackMessage && (
              <div
                style={{
                  borderRadius: 12,
                  padding: '10px 14px',
                  fontSize: 13,
                  display: 'flex',
                  alignItems: 'center',
                  gap: 10,
                  backgroundColor:
                    feedbackTone === 'success'
                      ? 'rgba(34, 197, 94, 0.12)'
                      : 'rgba(248, 113, 113, 0.12)',
                  color: feedbackTone === 'success' ? '#bbf7d0' : '#fecaca',
                  border: `1px solid ${
                    feedbackTone === 'success'
                      ? 'rgba(34, 197, 94, 0.4)'
                      : 'rgba(248, 113, 113, 0.35)'
                  }`,
                }}
              >
                {feedbackMessage}
              </div>
            )}

            {fileError && (
              <div
                style={{
                  borderRadius: 12,
                  padding: '10px 14px',
                  fontSize: 13,
                  backgroundColor: 'rgba(248, 113, 113, 0.12)',
                  color: '#fecaca',
                  border: '1px solid rgba(248, 113, 113, 0.35)',
                }}
              >
                {fileError}
              </div>
            )}

            {selectedPath ? (
              isFileLoading ? (
                <div style={{ ...EMPTY_STATE_STYLE, alignItems: 'flex-start', justifyContent: 'flex-start' }}>
                  <span style={{ fontSize: 13, color: '#94a3b8' }}>Cargando archivo…</span>
                </div>
              ) : (
                <pre style={FILE_CONTENT_STYLE}>{fileContent || 'El archivo está vacío.'}</pre>
              )
            ) : (
              <div style={EMPTY_STATE_STYLE}>
                <DocumentTextIcon style={{ width: 48, height: 48, color: 'rgba(148, 163, 184, 0.45)' }} aria-hidden />
                <div style={{ fontSize: 15, fontWeight: 500, color: '#cbd5f5' }}>
                  Selecciona un archivo para visualizarlo
                </div>
                <p style={{ fontSize: 13, color: '#94a3b8', textAlign: 'center', maxWidth: 320 }}>
                  Aquí verás una vista previa con tipografía monoespaciada y metadatos útiles del archivo elegido.
                </p>
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default SessionFilesViewer;
