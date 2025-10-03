"""
Global Conversation Context Manager

Maneja contexto conversacional con memoria TTL para resolución
de referencias ambiguas como "qué contiene?" sin filename específico.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import threading

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ConversationState:
    """Estado de conversación con TTL automático"""
    session_id: str
    user_id: str
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)

    # Entidades mencionadas recientemente
    last_file_accessed: Optional[str] = None
    last_branch_mentioned: Optional[str] = None
    recent_files: List[str] = field(default_factory=list)
    recent_operations: List[Dict[str, Any]] = field(default_factory=list)

    # Contexto de dominio específico
    current_analysis_type: Optional[str] = None
    preferred_file_format: Optional[str] = None

    def is_expired(self, ttl_minutes: int = 30) -> bool:
        """Verifica si el contexto ha expirado"""
        expiry_time = self.last_activity + timedelta(minutes=ttl_minutes)
        return datetime.now() > expiry_time

    def update_activity(self) -> None:
        """Actualiza timestamp de última actividad"""
        self.last_activity = datetime.now()

    def add_file_reference(self, filename: str) -> None:
        """Agrega referencia a archivo accedido"""
        self.last_file_accessed = filename
        if filename not in self.recent_files:
            self.recent_files.append(filename)
            # Mantener solo los últimos 5
            if len(self.recent_files) > 5:
                self.recent_files.pop(0)
        self.update_activity()

    def add_operation(self, operation: str, details: Dict[str, Any]) -> None:
        """Registra operación realizada"""
        operation_record = {
            'operation': operation,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.recent_operations.append(operation_record)
        # Mantener solo las últimas 10
        if len(self.recent_operations) > 10:
            self.recent_operations.pop(0)
        self.update_activity()


class GlobalConversationContext:
    """
    Gestor global de contexto conversacional con limpieza automática

    Reemplaza la gestión fragmentada de contexto distribuida
    por diferentes componentes del sistema.
    """

    def __init__(self, ttl_minutes: int = 30, cleanup_interval: int = 300):
        """
        Args:
            ttl_minutes: Tiempo de vida del contexto en minutos
            cleanup_interval: Intervalo de limpieza en segundos
        """
        self.contexts: Dict[str, ConversationState] = {}
        self.ttl_minutes = ttl_minutes
        self._lock = threading.RLock()

        # Iniciar limpieza automática
        self._start_cleanup_thread(cleanup_interval)

        logger.info({"event": "global_context_manager_initialized",
                    "ttl_minutes": ttl_minutes,
                    "cleanup_interval": cleanup_interval})

    def get_or_create_context(self, session_id: str, user_id: str = "global") -> ConversationState:
        """Obtiene o crea contexto de conversación"""
        with self._lock:
            if session_id not in self.contexts:
                self.contexts[session_id] = ConversationState(
                    session_id=session_id,
                    user_id=user_id
                )
                logger.info({"event": "conversation_context_created",
                           "session_id": session_id, "user_id": user_id})

            context = self.contexts[session_id]
            context.update_activity()
            return context

    def track_file_access(self, session_id: str, filename: str, operation: str,
                         details: Optional[Dict[str, Any]] = None) -> None:
        """Rastrea acceso a archivo"""
        context = self.get_or_create_context(session_id)

        context.add_file_reference(filename)
        context.add_operation(f"file_{operation}", {
            'filename': filename,
            'operation': operation,
            **(details or {})
        })

        logger.info({"event": "file_access_tracked",
                    "session_id": session_id,
                    "filename": filename,
                    "operation": operation})

    def track_branch_reference(self, session_id: str, branch_name: str) -> None:
        """Rastrea referencia a sucursal"""
        context = self.get_or_create_context(session_id)
        context.last_branch_mentioned = branch_name
        context.update_activity()

        logger.info({"event": "branch_reference_tracked",
                    "session_id": session_id,
                    "branch": branch_name})

    def resolve_file_reference(self, session_id: str, query: str) -> Optional[str]:
        """
        Resuelve referencia de archivo desde contexto

        Args:
            session_id: ID de sesión
            query: Query que puede contener referencia ambigua

        Returns:
            Filename si se puede resolver desde contexto
        """
        with self._lock:
            if session_id not in self.contexts:
                return None

            context = self.contexts[session_id]

            # Si la query es muy vaga, usar último archivo
            vague_indicators = [
                "que contiene",
                "que tiene",
                "qué hay",
                "contenido",
                "dentro"
            ]

            is_vague = any(indicator in query.lower() for indicator in vague_indicators)
            has_no_filename = not any(
                word in query.lower()
                for word in ["archivo", "documento", "llama", "llamado"]
            )

            if is_vague and has_no_filename and context.last_file_accessed:
                logger.info({"event": "file_reference_resolved_from_context",
                           "session_id": session_id,
                           "resolved_file": context.last_file_accessed,
                           "query": query})
                return context.last_file_accessed

            return None

    def get_recent_files(self, session_id: str, limit: int = 5) -> List[str]:
        """Obtiene archivos accedidos recientemente"""
        with self._lock:
            if session_id not in self.contexts:
                return []

            context = self.contexts[session_id]
            return context.recent_files[-limit:]

    def get_context_summary(self, session_id: str) -> Dict[str, Any]:
        """Obtiene resumen del contexto de conversación"""
        with self._lock:
            if session_id not in self.contexts:
                return {}

            context = self.contexts[session_id]
            return {
                'session_id': session_id,
                'user_id': context.user_id,
                'last_activity': context.last_activity.isoformat(),
                'last_file_accessed': context.last_file_accessed,
                'last_branch_mentioned': context.last_branch_mentioned,
                'recent_files_count': len(context.recent_files),
                'recent_operations_count': len(context.recent_operations),
                'current_analysis_type': context.current_analysis_type,
                'preferred_file_format': context.preferred_file_format
            }

    def set_analysis_preference(self, session_id: str, analysis_type: str,
                              file_format: Optional[str] = None) -> None:
        """Establece preferencias de análisis"""
        context = self.get_or_create_context(session_id)
        context.current_analysis_type = analysis_type
        if file_format:
            context.preferred_file_format = file_format

        logger.info({"event": "analysis_preference_set",
                    "session_id": session_id,
                    "analysis_type": analysis_type,
                    "file_format": file_format})

    def clear_context(self, session_id: str) -> bool:
        """Limpia contexto específico"""
        with self._lock:
            if session_id in self.contexts:
                del self.contexts[session_id]
                logger.info({"event": "context_cleared", "session_id": session_id})
                return True
            return False

    def _cleanup_expired_contexts(self) -> None:
        """Limpia contextos expirados"""
        with self._lock:
            expired_sessions = []

            for session_id, context in self.contexts.items():
                if context.is_expired(self.ttl_minutes):
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                del self.contexts[session_id]

            if expired_sessions:
                logger.info({"event": "expired_contexts_cleaned",
                           "count": len(expired_sessions),
                           "sessions": expired_sessions})

    def _start_cleanup_thread(self, interval_seconds: int) -> None:
        """Inicia thread de limpieza automática"""
        def cleanup_worker():
            while True:
                try:
                    time.sleep(interval_seconds)
                    self._cleanup_expired_contexts()
                except Exception as e:
                    logger.error({"event": "cleanup_thread_error", "error": str(e)})

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()

        logger.info({"event": "cleanup_thread_started", "interval": interval_seconds})

    def get_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas del context manager"""
        with self._lock:
            active_contexts = len(self.contexts)
            total_files_tracked = sum(
                len(ctx.recent_files) for ctx in self.contexts.values()
            )
            total_operations = sum(
                len(ctx.recent_operations) for ctx in self.contexts.values()
            )

            return {
                'active_contexts': active_contexts,
                'total_files_tracked': total_files_tracked,
                'total_operations': total_operations,
                'ttl_minutes': self.ttl_minutes
            }


# Singleton global para el proyecto
_global_context_manager: Optional[GlobalConversationContext] = None


def get_global_context_manager() -> GlobalConversationContext:
    """Obtiene instancia singleton del context manager"""
    global _global_context_manager
    if _global_context_manager is None:
        _global_context_manager = GlobalConversationContext()
    return _global_context_manager