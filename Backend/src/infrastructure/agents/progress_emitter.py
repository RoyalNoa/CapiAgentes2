from __future__ import annotations

from dataclasses import dataclass
from textwrap import shorten
from typing import Dict, Optional

from src.core.logging import get_logger
from src.infrastructure.streaming.realtime_event_bus import get_event_bus

logger = get_logger(__name__)


_AGENT_LABELS = {
    'capi_datab': 'Sistema financiero',
    'capidatab': 'Sistema financiero',
    'database_query': 'Sistema financiero',
    'capi_elcajas': 'Control de cajas',
    'capielcajas': 'Control de cajas',
    'branch_operations': 'Control de cajas',
    'capi_desktop': 'Gestor de archivos',
    'capidesktop': 'Gestor de archivos',
    'desktop_operation': 'Gestor de archivos',
    'capi_noticias': 'Monitor de noticias',
    'capinoticias': 'Monitor de noticias',
    'news_analysis': 'Monitor de noticias',
    'summary': 'Resúmenes financieros',
    'summaryagent': 'Resúmenes financieros',
    'summary_generation': 'Resúmenes financieros',
    'branch': 'Análisis por sucursal',
    'branchagent': 'Análisis por sucursal',
    'branch_analysis': 'Análisis por sucursal',
    'anomaly': 'Detección de anomalías',
    'anomalyagent': 'Detección de anomalías',
    'anomaly_detection': 'Detección de anomalías',
    'smalltalk': 'Asistente conversacional',
    'smalltalkfallbackagent': 'Asistente conversacional',
    'conversation': 'Asistente conversacional',
    'agente_g': 'Agente Google Workspace',
}

_AGENT_ACTIONS = {
    'capi_datab': 'database_query',
    'capidatab': 'database_query',
    'database_query': 'database_query',
    'capi_elcajas': 'branch_operations',
    'capielcajas': 'branch_operations',
    'branch_operations': 'branch_operations',
    'capi_desktop': 'desktop_operation',
    'capidesktop': 'desktop_operation',
    'desktop_operation': 'desktop_operation',
    'capi_noticias': 'news_analysis',
    'capinoticias': 'news_analysis',
    'news_analysis': 'news_analysis',
    'summary': 'summary_generation',
    'summaryagent': 'summary_generation',
    'summary_generation': 'summary_generation',
    'branch': 'branch_analysis',
    'branchagent': 'branch_analysis',
    'branch_analysis': 'branch_analysis',
    'anomaly': 'anomaly_detection',
    'anomalyagent': 'anomaly_detection',
    'anomaly_detection': 'anomaly_detection',
    'smalltalk': 'conversation',
    'smalltalkfallbackagent': 'conversation',
    'conversation': 'conversation',
    'agente_g': 'workspace_operation',
}

_STAGE_TONE = {
    'start': 'progress',
    'progress': 'progress',
    'success': 'success',
    'error': 'error',
}

_MAX_CONTENT = 200


def _label_for(agent_name: str) -> str:
    normalized = agent_name.lower()
    return _AGENT_LABELS.get(normalized, agent_name.replace('_', ' ').replace('-', ' ').title())


def _action_for(agent_name: str, fallback: Optional[str] = None) -> str:
    normalized = agent_name.lower()
    if normalized in _AGENT_ACTIONS:
        return _AGENT_ACTIONS[normalized]
    if fallback:
        return fallback
    return 'agent_action'


def _short_text(value: Optional[str], limit: int = _MAX_CONTENT) -> Optional[str]:
    if not value:
        return None
    return shorten(str(value).strip(), width=limit, placeholder='…')


def _pick_first(*values: Optional[str]) -> Optional[str]:
    for value in values:
        if value:
            stripped = str(value).strip()
            if stripped:
                return stripped
    return None


@dataclass(slots=True)
class AgentProgressEmitter:
    """Broadcast human-friendly lifecycle messages for agents."""

    def start(
        self,
        agent_name: str,
        session_id: Optional[str],
        *,
        query: Optional[str] = None,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        branch: Optional[str] = None,
        extra: Optional[Dict[str, object]] = None,
    ) -> None:
        content = self._compose_message(
            agent_name,
            stage='start',
            query=query,
            operation=operation,
            table=table,
            branch=branch,
        )
        self._emit(
            agent_name,
            session_id,
            stage='start',
            content=content,
            query=query,
            operation=operation,
            table=table,
            branch=branch,
            extra=extra,
        )

    def progress(
        self,
        agent_name: str,
        session_id: Optional[str],
        *,
        message: Optional[str] = None,
        detail: Optional[str] = None,
        extra: Optional[Dict[str, object]] = None,
    ) -> None:
        content = self._compose_message(
            agent_name,
            stage='progress',
            detail=_pick_first(message, detail),
        )
        self._emit(agent_name, session_id, stage='progress', content=content, detail=detail, extra=extra)

    def success(
        self,
        agent_name: str,
        session_id: Optional[str],
        *,
        detail: Optional[str] = None,
        rowcount: Optional[int] = None,
        branch: Optional[str] = None,
        extra: Optional[Dict[str, object]] = None,
    ) -> None:
        content = self._compose_message(
            agent_name,
            stage='success',
            detail=detail,
            rowcount=rowcount,
            branch=branch,
        )
        self._emit(
            agent_name,
            session_id,
            stage='success',
            content=content,
            detail=detail,
            rowcount=rowcount,
            branch=branch,
            extra=extra,
        )

    def error(
        self,
        agent_name: str,
        session_id: Optional[str],
        *,
        detail: Optional[str] = None,
        extra: Optional[Dict[str, object]] = None,
    ) -> None:
        content = self._compose_message(agent_name, stage='error', detail=detail)
        self._emit(agent_name, session_id, stage='error', content=content, detail=detail, extra=extra)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _compose_message(
        self,
        agent_name: str,
        *,
        stage: str,
        query: Optional[str] = None,
        detail: Optional[str] = None,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        rowcount: Optional[int] = None,
        branch: Optional[str] = None,
    ) -> Optional[str]:
        label = _label_for(agent_name)
        if stage == 'start':
            if operation:
                verb_map = {
                    'select': 'Consultando',
                    'insert': 'Insertando',
                    'update': 'Actualizando',
                    'delete': 'Eliminando',
                }
                verb = verb_map.get(operation.lower())
                if verb:
                    target = f" {table}" if table else ' datos'
                    suffix = f" ({branch})" if branch else ''
                    return _short_text(f"{verb}{target}{suffix}…")
            if query:
                return _short_text(f"{label}: {query}")
            return f"{label} en ejecución…"
        if stage == 'success':
            if detail:
                return _short_text(detail)
            if rowcount is not None:
                suffix = f" ({branch})" if branch else ''
                return _short_text(f"{label}: {rowcount} registros procesados{suffix}.")
            return f"{label} completado."
        if stage == 'error':
            if detail:
                return _short_text(f"{label} reporta: {detail}")
            return f"{label} encontró un problema."
        if detail:
            return _short_text(detail)
        return None

    def _emit(
        self,
        agent_name: str,
        session_id: Optional[str],
        *,
        stage: str,
        content: Optional[str],
        query: Optional[str] = None,
        detail: Optional[str] = None,
        operation: Optional[str] = None,
        table: Optional[str] = None,
        rowcount: Optional[int] = None,
        branch: Optional[str] = None,
        extra: Optional[Dict[str, object]] = None,
    ) -> None:
        if not content:
            return
        try:
            bus = get_event_bus()
        except Exception as exc:
            logger.warning('Agent progress bus unavailable', extra={'agent': agent_name, 'error': str(exc)})
            return
        normalized_session = session_id or 'global'
        tone = _STAGE_TONE.get(stage, 'info')
        metadata: Dict[str, object] = {
            'content': content,
            'stage': stage,
            'tone': tone,
            'action': _action_for(agent_name, extra.get('action') if extra else None),
        }
        if query:
            metadata['query'] = _short_text(query, limit=140)
        if detail and stage != 'success':
            metadata.setdefault('detail', _short_text(detail, limit=180))
        if operation:
            metadata.setdefault('operation', operation)
        if table:
            metadata.setdefault('table', table)
        if rowcount is not None:
            metadata.setdefault('rowcount', rowcount)
        if branch:
            metadata.setdefault('branch', branch)
        if extra:
            metadata.update({k: v for k, v in extra.items() if v is not None})
        try:
            bus.emit_agent_progress(
                agent=agent_name,
                session_id=normalized_session,
                content=content,
                metadata=metadata,
            )
        except Exception as exc:
            logger.warning('Failed to emit agent progress event', extra={
                'agent': agent_name,
                'stage': stage,
                'error': str(exc),
            })


agent_progress = AgentProgressEmitter()
