"""
Base node interfaces for LangGraph execution in our architecture.
Each node gets and returns a GraphState, possibly with side effects via adapters.
EXPERT INTEGRATION: WebSocket event broadcasting for real-time agent visualization.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional
import asyncio
import time
from contextlib import suppress
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator, WorkflowStatus
from src.core.logging import get_logger

# EXPERT INTEGRATION: Import WebSocket event broadcaster
from src.infrastructure.websocket.event_broadcaster import get_event_broadcaster

logger = get_logger(__name__)


class GraphNode(ABC):
    name: str

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or self.__class__.__name__

    @abstractmethod
    def run(self, state: GraphState) -> GraphState:
        """Execute node logic, returning a new GraphState."""
        raise NotImplementedError

    def _emit_async_event(self, coro, description: str) -> None:
        """Schedule broadcaster coroutine for immediate execution."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # No running loop -> safe to run synchronously
            try:
                asyncio.run(coro)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(f"Failed to emit {description}: {exc}")
        else:
            # CRITICAL FIX: Use run_coroutine_threadsafe for true immediate execution
            # This forces the event to be sent RIGHT NOW, not queued
            async def _emit_with_flush():
                try:
                    await coro
                    # Force immediate flush by yielding control
                    await asyncio.sleep(0)
                except Exception as exc:
                    logger.warning(f"Failed to emit {description}: {exc}")

            # Force immediate execution - this is the key!
            future = asyncio.run_coroutine_threadsafe(_emit_with_flush(), loop)
            # Don't wait for result - fire and forget
            future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)

    def _get_action_type(self) -> str:
        """
        Map node/agent name to semantic action type for frontend display.

        Returns semantic action string that frontend maps to Spanish gerund messages.

        Examples:
            'IntentNode' → 'intent'
<<<<<<< HEAD
            'SummaryNode' → 'summary_generation'
=======
            'CapiGusNode' → 'conversation_summary'
>>>>>>> origin/develop
            'CapiDataBNode' → 'database_query'
        """
        node_name = self.name.lower()

        # Comprehensive action map - 40+ mappings
        action_map = {
            # Orchestration nodes
            'start': 'start',
            'startnode': 'start',
            'intent': 'intent',
            'intentnode': 'intent',
            'router': 'router',
            'routernode': 'router',
            'supervisor': 'supervisor',
            'supervisornode': 'supervisor',
            'react': 'react',
            'reactnode': 'react',
            'reasoning': 'reasoning',
            'reasoningnode': 'reasoning',
            'human_gate': 'human_gate',
            'humangatenode': 'human_gate',
            'assemble': 'assemble',
            'assemblenode': 'assemble',
            'finalize': 'finalize',
            'finalizenode': 'finalize',

<<<<<<< HEAD
            # Agent nodes - Summary
            'summary': 'summary_generation',
            'summarynode': 'summary_generation',
            'summaryagent': 'summary_generation',
=======
            # Agent nodes - Conversational response (Capi Gus)
            'capi_gus': 'conversation_summary',
            'capigus': 'conversation_summary',
            'capi_gusnode': 'conversation_summary',
            'capigusnode': 'conversation_summary',
            'capigusagent': 'conversation_summary',
            'summary': 'conversation_summary',
            'summarynode': 'conversation_summary',
            'summaryagent': 'conversation_summary',
>>>>>>> origin/develop

            # Agent nodes - Branch
            'branch': 'branch_analysis',
            'branchnode': 'branch_analysis',
            'branchagent': 'branch_analysis',

            # Agent nodes - Anomaly
            'anomaly': 'anomaly_detection',
            'anomalynode': 'anomaly_detection',
            'anomalyagent': 'anomaly_detection',

            # Agent nodes - CapiDataB
            'capi_datab': 'database_query',    # CRITICAL: Con guion bajo (nombre real)
            'capidatab': 'database_query',
            'capidatabnode': 'database_query',
            'datab': 'database_query',
            'databnode': 'database_query',

            # Agent nodes - CapiElCajas
            'capi_elcajas': 'branch_operations',  # CRITICAL: Con guion bajo (nombre real)
            'capielcajas': 'branch_operations',
            'capielcajasnode': 'branch_operations',
            'elcajas': 'branch_operations',

            # Agent nodes - CapiDesktop
            'capi_desktop': 'desktop_operation',  # CRITICAL: Con guion bajo (nombre real)
            'capidesktop': 'desktop_operation',
            'capidesktopnode': 'desktop_operation',
            'desktop': 'desktop_operation',

            # Agent nodes - CapiNoticias
            'capi_noticias': 'news_analysis',   # CRITICAL: Con guion bajo (nombre real)
            'capinoticias': 'news_analysis',
            'capinoticiasnode': 'news_analysis',
            'noticias': 'news_analysis',

<<<<<<< HEAD
            # Agent nodes - Smalltalk
            'smalltalk': 'conversation',
            'smalltalknode': 'conversation',
            'smalltalkagent': 'conversation',
=======
            # Agent nodes - Capi Gus
>>>>>>> origin/develop
        }

        return action_map.get(node_name, 'agent_start')

    def _emit_agent_start(self, state: GraphState):
        """Emit WebSocket event when agent starts with semantic action type."""

        if hasattr(self, "_is_agent_node") and self._is_agent_node:
            # NOTA: Se eliminó event bus paralelo - no funcionaba con GIL de Python
            # Los eventos se envían en batch al final por diseño de LangGraph
            # La simulación de streaming se hace en el frontend
            broadcaster = get_event_broadcaster()

            # NUEVO: Get semantic action type
            action = self._get_action_type()

            # CAMBIO CRÍTICO: Generar mensaje de inicio contextual
            start_messages = {
                'financial_summary': 'Analizando resumen financiero...',
                'branch_analysis': 'Evaluando rendimiento por sucursal...',
                'anomaly_detection': 'Detectando anomalías financieras...',
                'general_query': 'Procesando consulta...',
                'database_query': 'Consultando base de datos...',
                'desktop_operation': 'Ejecutando operación de escritorio...'
            }

            content = start_messages.get(action, f'Procesando con {self.name}...')

            # Build metadata con contenido
            meta = {
                "trace_id": state.trace_id,
                "node": self.name,
                "content": content  # Agregar contenido contextual
            }

            # NUEVO: Extract target_agent from state metadata for inter-agent visualization
            if state.response_metadata:
                semantic_result = state.response_metadata.get("semantic_result", {})

                if semantic_result.get("target_agent"):
                    meta["target_agent"] = semantic_result["target_agent"]

                if semantic_result.get("routing_agent"):
                    meta["routing_agent"] = semantic_result["routing_agent"]

            self._emit_async_event(
                broadcaster.broadcast_agent_start(
                    agent_name=self.name,
                    session_id=state.session_id or "unknown",
                    action=action,  # ← NUEVO: pasar action type
                    meta=meta       # ← INCLUYE target_agent si existe
                ),
                "agent_start event"
            )

    def _emit_agent_end(self, state: GraphState, success: bool = True, duration_ms: Optional[float] = None):
        """Emit WebSocket event when agent ends with actual task content."""

        if hasattr(self, "_is_agent_node") and self._is_agent_node:
            # NOTA: Se eliminó event bus - simulación se hace en frontend
            broadcaster = get_event_broadcaster()

            # CAMBIO CRÍTICO: Extraer el mensaje real del estado para enviarlo en el evento
            # Esto permite que el frontend muestre el contenido real de la tarea
            task_content = None

            # Buscar contenido en múltiples campos posibles del state
            if hasattr(state, 'response_message') and state.response_message:
                # Usar el mensaje de respuesta si está disponible
                task_content = str(state.response_message)[:200]
            elif hasattr(state, 'current_task') and state.current_task:
                # Fallback a tarea actual
                task_content = str(state.current_task)[:200]
            elif hasattr(state, 'last_message') and state.last_message:
                # Último mensaje procesado
                task_content = str(state.last_message)[:200]
            elif hasattr(state, 'messages') and state.messages:
                # Último mensaje de la lista
                last_msg = state.messages[-1] if isinstance(state.messages, list) else None
                if last_msg:
                    if isinstance(last_msg, dict) and 'content' in last_msg:
                        task_content = str(last_msg['content'])[:200]
                    else:
                        task_content = str(last_msg)[:200]

            # Si aún no hay contenido, generar uno basado en el agente
            if not task_content:
                agent_messages = {
                    'summary': 'Resumen financiero completado',
                    'branch': 'Análisis de sucursal completado',
                    'anomaly': 'Detección de anomalías completada',
                    'capi_datab': 'Consulta de base de datos completada',
                    'capi_desktop': 'Operación de escritorio completada',
                    'capi_elcajas': 'Análisis de cajas completado',
<<<<<<< HEAD
                    'smalltalk': 'Respuesta generada'
=======
>>>>>>> origin/develop
                }
                task_content = agent_messages.get(self.name, f'Tarea completada por {self.name}')

            meta_data = {
                "trace_id": state.trace_id,
                "node": self.name
            }

            # Agregar content al meta si existe
            if task_content:
                meta_data["content"] = task_content

            self._emit_async_event(
                broadcaster.broadcast_agent_end(
                    agent_name=self.name,
                    session_id=state.session_id or "unknown",
                    success=success,
                    duration_ms=duration_ms,
                    action='agent_end',  # ← NUEVO: explicit action type
                    meta=meta_data
                ),
                "agent_end event"
            )


class StartNode(GraphNode):
    def run(self, state: GraphState) -> GraphState:
        logger.debug({"event": "StartNode", "node": self.name})
        s = StateMutator.update_field(state, "status", WorkflowStatus.PROCESSING)
        s = StateMutator.update_field(s, "current_node", self.name)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)
        return s


class FinalizeNode(GraphNode):
    def run(self, state: GraphState) -> GraphState:
        logger.debug({"event": "FinalizeNode", "node": self.name})
        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)
        # If no response was set, provide a minimal fallback
        if not s.response_message:
            s = StateMutator.update_field(
                s, "response_message", "Lo siento, no pude generar una respuesta en este momento."
            )
        s = StateMutator.update_field(s, "status", WorkflowStatus.COMPLETED)
        return s
