"""
Graph runtime adapter: wires builder + state + persistence into a callable orchestrator-like API.
Provides a clean contract: process_query(session_id, user_id, text) -> ResponseEnvelope
"""
from __future__ import annotations

import asyncio
import json
import os
import sqlite3
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
try:
    from langgraph.checkpoint.sqlite import SqliteSaver
except ImportError:  # pragma: no cover - optional backend
    SqliteSaver = None

from src.infrastructure.langgraph.state_schema import GraphState, WorkflowStatus, StateMutator
from src.infrastructure.langgraph.graph_builder import GraphBuilder
from src.infrastructure.langgraph.dynamic_graph_builder import DynamicGraphManager
from src.infrastructure.langgraph.nodes.base import StartNode, FinalizeNode
from src.infrastructure.langgraph.nodes.intent_node import IntentNode
from src.infrastructure.langgraph.nodes.react_node import ReActNode
from src.infrastructure.langgraph.nodes.reasoning_node import ReasoningNode
from src.infrastructure.langgraph.nodes.supervisor_node import SupervisorNode
from src.infrastructure.langgraph.nodes.router_node import RouterNode
from src.infrastructure.langgraph.nodes.loop_controller_node import LoopControllerNode
from src.infrastructure.langgraph.nodes.capi_gus_node import CapiGusNode
from src.infrastructure.langgraph.nodes.branch_node import BranchNode
from src.infrastructure.langgraph.nodes.anomaly_node import AnomalyNode
from src.infrastructure.langgraph.nodes.capi_desktop_node import CapiDesktopNode
from src.infrastructure.langgraph.nodes.capi_datab_node import CapiDataBNode
from src.infrastructure.langgraph.nodes.capi_elcajas_node import CapiElCajasNode
from src.infrastructure.langgraph.nodes.human_gate_node import HumanGateNode
from src.infrastructure.langgraph.nodes.assemble_node import AssembleNode
try:
    from src.infrastructure.langgraph.nodes.capi_noticias_node import CapiNoticiasNode
    _FALLBACK_NEWS_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _FALLBACK_NEWS_AVAILABLE = False

# Servicios dinámicos de agentes
from src.application.services.agent_registry_service import (
    AgentRegistryService,
    FileAgentRegistryRepository,
)
from src.application.services.agent_config_service import AgentConfigService
from src.shared.agent_config_repository import FileAgentConfigRepository
from src.domain.agents.agent_models import IntentType, ResponseEnvelope, ResponseType
from src.core.logging import get_logger
from src.infrastructure.websocket.event_broadcaster import get_event_broadcaster
from src.infrastructure.workspace.session_storage import SessionStorage

logger = get_logger(__name__)


class LangGraphRuntime:
    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.event_broadcaster = get_event_broadcaster()
        self._interrupt_before_nodes = tuple(
            self.config.get("interrupt_before_nodes", ())
        )
        self.checkpointer, self._checkpoint_connection = self._create_checkpointer()

        # Inicializar sistema dinámico / fallback estático
        self._init_dynamic_system()

        self.builder = GraphBuilder()
        self.static_graph = self.builder.build_minimal(
            checkpointer=self.checkpointer,
            interrupt_before=self._interrupt_before_nodes,
        )

        self.session_storage = SessionStorage()

        prefer_dynamic = bool(self.config.get("enable_dynamic_graph", False))
        if prefer_dynamic and self.dynamic_manager:
            try:
                self.graph = self.dynamic_manager.initialize_graph()
            except Exception as exc:  # pragma: no cover - fallback
                logger.error({"event": "dynamic_graph_init_failed", "error": str(exc)})
                self.graph = self.static_graph
        else:
            self.graph = self.static_graph

    # ------------------------------------------------------------------
    # Inicialización y recursos
    # ------------------------------------------------------------------

    def _create_checkpointer(self) -> tuple[BaseCheckpointSaver, Optional[sqlite3.Connection]]:
        backend = (self.config.get("checkpoint_backend") or os.getenv("LANGGRAPH_CHECKPOINT_BACKEND") or "sqlite").lower()
        if backend == "sqlite" and SqliteSaver is not None:
            db_path = self._resolve_checkpoint_path()
            conn = sqlite3.connect(db_path, check_same_thread=False)
            saver = SqliteSaver(conn)
            saver.setup()
            logger.info({
                "event": "checkpoint_initialized",
                "backend": "sqlite",
                "path": str(db_path),
            })
            return saver, conn

        logger.warning({
            "event": "checkpoint_fallback",
            "backend": backend,
            "reason": "using in-memory saver",
        })
        return MemorySaver(), None

    def _resolve_checkpoint_path(self) -> Path:
        raw_path = self.config.get("checkpoint_path") or os.getenv("LANGGRAPH_CHECKPOINT_PATH")
        if raw_path:
            path = Path(raw_path)
        else:
            logs_dir = Path.cwd() / "logs" / "langgraph"
            logs_dir.mkdir(parents=True, exist_ok=True)
            path = logs_dir / "checkpoints.sqlite"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _init_dynamic_system(self) -> None:
        try:
            config_repo = FileAgentConfigRepository()
            config_service = AgentConfigService(repo=config_repo)
            registry_repo = FileAgentRegistryRepository()
            registry_service = AgentRegistryService(
                registry_repo=registry_repo,
                config_service=config_service,
            )
            self.dynamic_manager = DynamicGraphManager(
                registry_service,
                checkpointer=self.checkpointer,
                interrupt_before=self._interrupt_before_nodes,
            )
            self.registry_service = registry_service
            logger.info("Dynamic agent system initialized successfully")
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({"event": "dynamic_init_failed", "error": str(exc)})
            self.dynamic_manager = None
            self.registry_service = None

    def close(self) -> None:
        if self._checkpoint_connection is not None:
            with suppress(Exception):
                self._checkpoint_connection.close()

    # ------------------------------------------------------------------
    # Ejecución principal
    # ------------------------------------------------------------------

    def _initial_state(self, session_id: str, user_id: str, text: str) -> GraphState:
        payload: Dict[str, Any] = {}
        query_text = text or ""
        workflow_mode = "chat"

        if text:
            try:
                parsed = json.loads(text)
            except ValueError:
                parsed = None
            if isinstance(parsed, dict):
                payload = parsed
                query_text = str(parsed.get("query") or parsed.get("text") or "")
                workflow_mode = str(parsed.get("workflow_mode") or parsed.get("mode") or workflow_mode)

        config = dict(self.config or {})
        config.setdefault("workflow_mode", workflow_mode)
        if payload:
            config["external_payload"] = payload

        return GraphState(
            session_id=session_id,
            trace_id=f"trace-{datetime.now().timestamp()}",
            user_id=user_id,
            original_query=query_text,
            workflow_mode=workflow_mode,
            external_payload=payload,
            config=config,
        )

    def _execution_config(self, session_id: str) -> Dict[str, Any]:
        configurable = {
            "thread_id": session_id,
            "checkpoint_id": session_id,
        }
        return {"configurable": configurable}

    def process_query(self, session_id: str, user_id: str, text: str) -> ResponseEnvelope:
        logger.info(
            {
                "event": "runtime_process_query_start",
                "session_id": session_id,
                "user_id": user_id,
            }
        )
        if self.graph is None:
            raise RuntimeError("LangGraph runtime graph not initialized")

        state = self._initial_state(session_id, user_id, text)
        config = self._execution_config(session_id)

        final_state = self._run_with_stream(
            graph_input=state,
            config=config,
            session_id=session_id,
            initial_state=state,
        )
        if final_state is None:
            logger.warning({"event": "runtime_final_state_missing", "session_id": session_id})
            final_state = state
        interrupt_data = getattr(final_state, '__interrupt__', None)
        metadata = final_state.response_metadata if isinstance(getattr(final_state, 'response_metadata', None), dict) else {}
        pending_human = bool(interrupt_data) or bool(metadata.get('el_cajas_pending')) or bool(metadata.get('actions'))
        if (not final_state.completed_nodes or final_state.status == WorkflowStatus.INITIALIZED) and not pending_human:
            final_state = self._manual_fallback(state)

        self._persist_session_state(final_state)

        final_trace_id = getattr(final_state, 'trace_id', None)
        final_status = getattr(final_state, 'status', None)
        final_completed = getattr(final_state, 'completed_nodes', [])
        final_errors = len(getattr(final_state, 'errors', []) or [])
        logger.info(
            {
                "event": "runtime_process_query_end",
                "session_id": session_id,
                "trace_id": final_trace_id,
                "status": final_status.value if hasattr(final_status, 'value') else final_status,
                "completed_nodes": final_completed,
                "errors": final_errors,
            }
        )
        return self._map_state_to_envelope(final_state)

    def get_session_history(self, session_id: str) -> List[Dict[str, Any]]:
        try:
            return self.session_storage.get_session_history(session_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                {
                    "event": "session_history_load_failed",
                    "session_id": session_id,
                    "error": str(exc),
                }
            )
            return []

    def get_active_sessions(self) -> List[str]:
        try:
            return self.session_storage.list_sessions()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning({"event": "session_list_failed", "error": str(exc)})
            return []

    def clear_session_history(self, session_id: str) -> None:
        try:
            self.session_storage.clear_session_history(session_id)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                {
                    "event": "session_history_clear_failed",
                    "session_id": session_id,
                    "error": str(exc),
                }
            )

    def _run_with_stream(
        self,
        *,
        graph_input: Any,
        config: Dict[str, Any],
        session_id: str,
        initial_state: GraphState | None = None,
    ) -> GraphState:
        graph = self.graph
        assert graph is not None

        stream_modes: Iterable[str] = ("updates", "values")
        current_state: GraphState | None = initial_state
        last_node = (initial_state.current_node if initial_state else None) or "start"

        for item in graph.stream(
            graph_input,
            config,
            stream_mode=stream_modes,
            interrupt_before=self._interrupt_before_nodes,
        ):
            if isinstance(item, tuple) and len(item) == 2:
                mode, payload = item
            else:
                mode, payload = "values", item

            if mode == "updates" and isinstance(payload, dict):
                current_state, last_node = self._handle_update_event(
                    current_state,
                    payload,
                    session_id,
                    last_node,
                )
            elif mode == "values":
                current_state = self._merge_state(current_state, payload)
                if current_state:
                    self._emit_state_snapshot(session_id, current_state)

        if current_state is None:
            raise RuntimeError("Graph execution did not yield state data")
        return current_state

    def _manual_fallback(self, seed_state: GraphState) -> GraphState:
        logger.warning({"event": "graph_stream_fallback", "reason": "empty_state"})
        state = seed_state
        orchestrator_chain = [
            StartNode(name="start"),
            IntentNode(name="intent"),
            ReActNode(name="react"),
            ReasoningNode(name="reasoning"),
            SupervisorNode(name="supervisor"),
            RouterNode(name="router"),
        ]
        for node in orchestrator_chain:
            state = node.run(state)

        decision = state.routing_decision or state.active_agent or "assemble"
        if decision == "human_gate":
            decision = "capi_gus"
        agent_nodes = {
            "capi_gus": CapiGusNode(name="capi_gus"),
            "branch": BranchNode(name="branch"),
            "anomaly": AnomalyNode(name="anomaly"),
            "capi_desktop": CapiDesktopNode(name="capi_desktop"),
            "capi_datab": CapiDataBNode(name="capi_datab"),
            "capi_elcajas": CapiElCajasNode(name="capi_elcajas"),
        }
        if _FALLBACK_NEWS_AVAILABLE:
            agent_nodes.setdefault("capi_noticias", CapiNoticiasNode(name="capi_noticias"))

        agent_node = agent_nodes.get(decision)
        if agent_node is not None:
            state = agent_node.run(state)
        else:
            logger.debug({"event": "fallback_agent_missing", "decision": decision})

        metadata = state.response_metadata if isinstance(state.response_metadata, dict) else {}
        if metadata.get('el_cajas_pending'):
            return state

        state = HumanGateNode(name="human_gate").run(state)
        state = AssembleNode(name="assemble").run(state)
        state = FinalizeNode(name="finalize").run(state)
        return state

    def _rebuild_state_from_manifest(self, session_id: str) -> Optional[GraphState]:
        manifest = self.session_storage.get_manifest(session_id)
        if not manifest:
            return None

        completed_nodes = list(manifest.get('completed_nodes') or [])
        if 'loop_controller' not in completed_nodes:
            completed_nodes.append('loop_controller')

        status_value = manifest.get('status') or WorkflowStatus.PROCESSING.value
        try:
            status_enum = WorkflowStatus(status_value)
        except ValueError:
            status_enum = WorkflowStatus.PROCESSING

        intent_value = manifest.get('intent')
        detected_intent = None
        if intent_value:
            try:
                detected_intent = IntentType(intent_value)
            except ValueError:
                detected_intent = None

        last_response = manifest.get('last_response') or {}
        state_payload = {
            'session_id': manifest.get('session_id') or session_id,
            'trace_id': manifest.get('trace_id') or f"{session_id}-manual-resume",
            'user_id': manifest.get('user_id') or 'user',
            'original_query': manifest.get('original_query') or manifest.get('last_query') or '',
            'workflow_mode': manifest.get('workflow_mode') or 'chat',
            'status': status_enum,
            'current_node': manifest.get('routing_decision') or 'human_gate',
            'completed_nodes': completed_nodes,
            'detected_intent': detected_intent,
            'intent_confidence': manifest.get('intent_confidence'),
            'routing_decision': manifest.get('routing_decision'),
            'active_agent': manifest.get('active_agent'),
            'conversation_history': manifest.get('conversation_history') or [],
            'memory_window': manifest.get('memory_window') or [],
            'reasoning_summary': manifest.get('reasoning_summary'),
            'processing_metrics': manifest.get('processing_metrics') or {},
            'response_message': last_response.get('message'),
            'response_data': last_response.get('data') or {},
            'response_metadata': manifest.get('response_metadata') or {},
            'shared_artifacts': manifest.get('shared_artifacts') or {},
            'errors': manifest.get('errors') or [],
        }
        return GraphState.model_validate(state_payload)

    def _manual_resume_human_gate(self, session_id: str, resume_payload: Dict[str, Any]) -> GraphState:
        state = self._rebuild_state_from_manifest(session_id)
        if state is None:
            raise RuntimeError(f"No session manifest available for {session_id}")

        metadata = dict(state.response_metadata or {})
        metadata['human_decision'] = resume_payload
        metadata['human_approved'] = bool(resume_payload.get('approved'))
        state = StateMutator.merge_dict(state, 'response_metadata', metadata)

        original_message = state.response_message or ''

        loop_node = LoopControllerNode()
        state = loop_node.run(state)
        next_node = state.routing_decision or state.active_agent or 'assemble'

        if next_node == 'capi_desktop':
            state = CapiDesktopNode().run(state)
            next_node = 'assemble'

        if next_node != 'finalize':
            state = AssembleNode().run(state)

        state = FinalizeNode().run(state)

        final_message = (state.response_message or '').strip()
        if original_message and original_message not in final_message:
            combined = f"{original_message}\n\n{final_message}" if final_message else original_message
            state = StateMutator.update_field(state, 'response_message', combined)

        self._persist_session_state(state)
        return state

        state = FinalizeNode(name="finalize").run(state)
        return state

    def _persist_session_state(self, state: GraphState | None) -> None:
        if state is None:
            logger.warning(
                {
                    "event": "session_state_missing",
                    "error": "Attempted to persist empty state",
                }
            )
            return
        try:
            self.session_storage.update_from_state(state)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning(
                {
                    "event": "session_state_persist_failed",
                    "session_id": getattr(state, 'session_id', None),
                    "error": str(exc),
                }
            )

    def _handle_update_event(
        self,
        current_state: GraphState | None,
        payload: Dict[str, Any],
        session_id: str,
        last_node: str | None,
    ) -> tuple[GraphState, str]:
        state = current_state
        next_node = last_node or "start"
        for node_name, node_update in payload.items():
            prev_node = next_node
            state = self._merge_state(state, node_update)
            if state:
                self._emit_state_snapshot(session_id, state)
                self._emit_transition(prev_node, node_name, session_id, state)
            next_node = node_name
        if state is None:
            raise RuntimeError("Unable to merge state from update payload")
        return state, next_node

    def _merge_state(self, state: GraphState | None, payload: Any) -> GraphState | None:
        if isinstance(payload, GraphState):
            return payload
        if isinstance(payload, dict):
            if state is None:
                try:
                    return GraphState.model_validate(payload)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.debug({"event": "state_merge_failed", "error": str(exc)})
                    return None
            try:
                return state.model_copy(update=payload)
            except Exception:
                try:
                    merged = state.model_dump(mode="json")
                    merged.update(payload)
                    return GraphState.model_validate(merged)
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.debug({"event": "state_merge_failed", "error": str(exc)})
                    return state
        return state

    def _emit_state_snapshot(self, session_id: str, state: GraphState) -> None:
        if not self.event_broadcaster or not session_id:
            return
        try:
            snapshot = state.to_frontend_format()
            self.event_broadcaster.update_session_state(session_id, snapshot)
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug({"event": "state_snapshot_failed", "error": str(exc)})

    def _map_node_to_action(self, node_name: str) -> str:
        """
        Map node name to semantic action type for frontend display.

        Args:
            node_name: Name of the node (e.g., "intent", "router", "capi_gus")

        Returns:
            Semantic action string (e.g., "intent", "router", "summary_generation")
        """
        node_lower = node_name.lower()

        action_map = {
            # Orchestration nodes
            'start': 'start',
            'intent': 'intent',
            'router': 'router',
            'supervisor': 'supervisor',
            'react': 'react',
            'reasoning': 'reasoning',
            'human_gate': 'human_gate',
            'assemble': 'assemble',
            'finalize': 'finalize',

            # Agent nodes
            'summary': 'summary_generation',
            'branch': 'branch_analysis',
            'anomaly': 'anomaly_detection',
            'capidatab': 'database_query',
            'capielcajas': 'branch_operations',
            'capidesktop': 'desktop_operation',
            'capi_gus': 'conversation',
            'capinoticias': 'news_analysis',
        }

        return action_map.get(node_lower, node_name.lower())


    def _emit_transition(
        self,
        from_node: Optional[str],
        to_node: Optional[str],
        session_id: str,
        state: GraphState,
    ) -> None:
        """Emit node transition event with semantic action type and inter-agent metadata."""

        if not self.event_broadcaster or not from_node or not to_node:
            return

        # NUEVO: Determine semantic action type based on target node
        action = self._map_node_to_action(to_node)

        # Build metadata
        meta = {
            "trace_id": state.trace_id,
            "completed_nodes": list(state.completed_nodes),
        }

        # NUEVO: Extract target_agent/routing_agent from state metadata
        if state.response_metadata:
            semantic_result = state.response_metadata.get("semantic_result", {})

            if semantic_result.get("target_agent"):
                meta["target_agent"] = semantic_result["target_agent"]

            if semantic_result.get("routing_agent"):
                meta["routing_agent"] = semantic_result["routing_agent"]

        coro = self.event_broadcaster.broadcast_node_transition(
            from_node,
            to_node,
            session_id,
            action=action,  # ← NUEVO: semantic action type
            meta=meta,      # ← INCLUYE target_agent/routing_agent
        )
        self._dispatch_async(coro, "node_transition")

    @staticmethod
    def _dispatch_async(coro, description: str) -> None:
        if coro is None:
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(coro)
            except Exception as exc:  # pragma: no cover
                logger.debug({"event": "async_dispatch_failed", "step": description, "error": str(exc)})
        else:
            # CRITICAL FIX: Use run_coroutine_threadsafe for true immediate execution
            # This forces the event to be sent RIGHT NOW, not queued
            async def _emit_with_flush():
                try:
                    await coro
                    # Force immediate flush by yielding control
                    await asyncio.sleep(0)
                except Exception as exc:
                    logger.debug({"event": "async_task_failed", "step": description, "error": str(exc)})

            # Force immediate execution - this is the key!
            future = asyncio.run_coroutine_threadsafe(_emit_with_flush(), loop)
            # Don't wait for result - fire and forget
            future.add_done_callback(lambda f: f.exception() if not f.cancelled() else None)

    # ------------------------------------------------------------------
    # Respuestas y metadatos
    # ------------------------------------------------------------------

    def _map_state_to_envelope(self, final_state: GraphState) -> ResponseEnvelope:
        resp_type = ResponseType.SUCCESS
        try:
            if (
                final_state.intent_confidence is not None
                and final_state.intent_confidence < 0.2
                and hasattr(ResponseType, "NOTICE")
            ):
                resp_type = ResponseType.NOTICE  # type: ignore[attr-defined]
        except Exception:
            pass

        meta: Dict[str, Any] = {
            "status": final_state.status.value,
            "completed_nodes": final_state.completed_nodes,
            "intent": getattr(final_state.detected_intent, "value", None),
            "intent_confidence": final_state.intent_confidence,
        }
        if final_state.reasoning_summary:
            meta["reasoning_summary"] = final_state.reasoning_summary
        if final_state.response_metadata:
            meta.setdefault("response_metadata", final_state.response_metadata)
            plan_meta = final_state.response_metadata.get("reasoning_plan")
            if plan_meta:
                meta.setdefault("reasoning_plan", plan_meta)
            react_trace = final_state.response_metadata.get("react_trace")
            if react_trace:
                meta.setdefault("react_trace", react_trace)
            supervisor_queue = final_state.response_metadata.get("supervisor_queue")
            if supervisor_queue:
                meta.setdefault("supervisor_queue", supervisor_queue)
            supervisor_selected = final_state.response_metadata.get("supervisor_selected")
            if supervisor_selected:
                meta.setdefault("supervisor_selected", supervisor_selected)
        if final_state.processing_metrics:
            meta.setdefault("processing_metrics", final_state.processing_metrics)

        message = final_state.response_message or ""
        interrupt_data = getattr(final_state, "__interrupt__", None)
        if interrupt_data:
            resp_type = ResponseType.NOTICE
            meta["requires_human"] = True
            meta["interrupt"] = [
                {
                    "id": getattr(interrupt, "id", None),
                    "value": getattr(interrupt, "value", None),
                }
                for interrupt in interrupt_data
            ]
            if not message:
                message = "Se requiere aprobacion humana para continuar."

        response_data = dict(final_state.response_data) if final_state.response_data else {}
        if final_state.shared_artifacts:
            response_data.setdefault("shared_artifacts", final_state.shared_artifacts)

        return ResponseEnvelope(
            trace_id=final_state.trace_id,
            response_type=resp_type,
            intent=(final_state.detected_intent or IntentType.UNKNOWN),
            message=message,
            data=response_data,
            meta=meta,
        )

    # ------------------------------------------------------------------
    # Gestión dinámica
    # ------------------------------------------------------------------

    def resume_human_gate(self, session_id: str, resume_payload: Dict[str, Any]) -> ResponseEnvelope:
        if self.graph is None:
            raise RuntimeError("LangGraph runtime graph not initialized")
        command = Command(resume=resume_payload)
        config = self._execution_config(session_id)
        try:
            final_state = self._run_with_stream(
                graph_input=command,
                config=config,
                session_id=session_id,
                initial_state=None,
            )
        except Exception as exc:  # pragma: no cover - fallback path
            logger.warning({"event": "manual_resume_human_gate", "session_id": session_id, "error": str(exc)})
            final_state = self._manual_resume_human_gate(session_id, resume_payload)
        return self._map_state_to_envelope(final_state)

    def register_agent_dynamically(self, agent_name: str) -> bool:
        if not self.dynamic_manager:
            logger.warning("Dynamic manager not available, cannot register agent dynamically")
            return False
        try:
            self.graph = self.dynamic_manager.register_agent_and_rebuild(agent_name)
            logger.info({"event": "agent_registered_dynamic", "agent": agent_name})
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({"event": "agent_register_failed", "agent": agent_name, "error": str(exc)})
            return False

    def unregister_agent_dynamically(self, agent_name: str) -> bool:
        if not self.dynamic_manager:
            logger.warning("Dynamic manager not available, cannot unregister agent dynamically")
            return False
        try:
            self.graph = self.dynamic_manager.unregister_agent_and_rebuild(agent_name)
            logger.info({"event": "agent_unregistered_dynamic", "agent": agent_name})
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({"event": "agent_unregister_failed", "agent": agent_name, "error": str(exc)})
            return False

    def refresh_dynamic_graph(self) -> bool:
        if not self.dynamic_manager:
            logger.warning("Dynamic manager not available, cannot refresh graph")
            return False
        try:
            self.graph = self.dynamic_manager.refresh_graph()
            logger.info("Dynamic graph refreshed successfully")
            return True
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({"event": "graph_refresh_failed", "error": str(exc)})
            return False

    def get_dynamic_graph_status(self) -> Dict[str, Any]:
        if not self.dynamic_manager:
            return {
                "dynamic_system_available": False,
                "error": "Dynamic manager not initialized",
            }
        try:
            return self.dynamic_manager.get_graph_status()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error({"event": "graph_status_failed", "error": str(exc)})
            return {
                "dynamic_system_available": True,
                "error": str(exc),
            }

    def is_dynamic_system_available(self) -> bool:
        return self.dynamic_manager is not None and self.registry_service is not None



