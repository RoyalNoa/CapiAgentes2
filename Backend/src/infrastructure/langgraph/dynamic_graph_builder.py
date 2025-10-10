#!/usr/bin/env python3
"""
CAPI - Dynamic Graph Builder
============================
Ruta: /Backend/src/infrastructure/langgraph/dynamic_graph_builder.py
Descripcion: GraphBuilder dinamico que puede registrar agentes en tiempo de ejecuciÃ³n
Estado: âš™ ACTIVO - Sistema dinamico de construccion de grafos
Dependencias: GraphBuilder, AgentRegistryService
PropÃ³sito: construccion dinÃ¡mica de grafos LangGraph con agentes registrados
PatrÃ³n: Builder Pattern + Factory Pattern + Registry Pattern
"""

from __future__ import annotations

import importlib
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple, Type

from langgraph.checkpoint.base import BaseCheckpointSaver

from src.core.logging import get_logger
from src.infrastructure.langgraph.graph_builder import GraphBuilder
from src.infrastructure.langgraph.nodes.base import GraphNode, StartNode, FinalizeNode
from src.infrastructure.langgraph.nodes.intent_node import IntentNode
from src.infrastructure.langgraph.nodes.react_node import ReActNode
from src.infrastructure.langgraph.nodes.reasoning_node import ReasoningNode
from src.infrastructure.langgraph.nodes.supervisor_node import SupervisorNode
from src.infrastructure.langgraph.nodes.loop_controller_node import LoopControllerNode
from src.infrastructure.langgraph.nodes.router_node import RouterNode
from src.infrastructure.langgraph.nodes.assemble_node import AssembleNode
from src.infrastructure.langgraph.nodes.capi_gus_node import CapiGusNode
from src.infrastructure.langgraph.nodes.branch_node import BranchNode
from src.infrastructure.langgraph.nodes.anomaly_node import AnomalyNode
from src.infrastructure.langgraph.nodes.capi_desktop_node import CapiDesktopNode
from src.infrastructure.langgraph.nodes.capi_datab_node import CapiDataBNode
from src.infrastructure.langgraph.nodes.capi_elcajas_node import CapiElCajasNode
from src.infrastructure.langgraph.nodes.capi_alertas_node import CapiAlertasNode
from src.infrastructure.langgraph.nodes.human_gate_node import HumanGateNode
try:  # Optional agent with heavy deps
    from src.infrastructure.langgraph.nodes.capi_noticias_node import CapiNoticiasNode
    _CAPI_NOTICIAS_AVAILABLE = True
except ImportError:  # pragma: no cover - optional feature
    _CAPI_NOTICIAS_AVAILABLE = False
from src.application.services.agent_registry_service import AgentManifest, AgentRegistryService
from src.infrastructure.langgraph.state_schema import GraphState

logger = get_logger(__name__)


class DynamicGraphBuilder(GraphBuilder):
    """GraphBuilder dinamico que construye grafos basado en los agentes registrados."""

    def __init__(
        self,
        registry_service: AgentRegistryService,
        *,
        checkpointer: BaseCheckpointSaver | None = None,
        interrupt_before: Iterable[str] | None = None,
    ) -> None:
        super().__init__()
        self.registry_service = registry_service
        self._node_cache: Dict[str, Type[GraphNode]] = {}
        self._graph_version: int = 0
        self._last_build_info: Dict[str, Any] = {}
        self._last_compiled_graph: Any | None = None
        self._core_agents: Set[str] = {
            "capi_gus",
            "branch",
            "anomaly",
            "capi_desktop",
            "capi_datab",
            "capi_elcajas",
            "capi_alertas",
        }
        if _CAPI_NOTICIAS_AVAILABLE:
            self._core_agents.add("capi_noticias")
        self._default_checkpointer = checkpointer
        self._default_interrupts = tuple(interrupt_before or ())

    # ------------------------------------------------------------------
    # Build entrypoint
    # ------------------------------------------------------------------

    def build_dynamic(
        self,
        *,
        rebuild_reason: str = "full_rebuild",
        agent_name: Optional[str] = None,
        checkpointer: BaseCheckpointSaver | None = None,
        interrupt_before: Iterable[str] | None = None,
    ) -> Any:
        logger.info(
            {
                "event": "dynamic_graph_build_start",
                "reason": rebuild_reason,
                "agent": agent_name,
            }
        )

        self.reset()
        self._add_core_nodes()
        self._add_registered_agent_nodes()
        self._setup_graph_edges()

        compiled = self._compile_state_graph(
            checkpointer=checkpointer or self._default_checkpointer,
            interrupt_before=interrupt_before or self._default_interrupts,
        )
        self._last_compiled_graph = compiled
        self._capture_build_snapshot(rebuild_reason=rebuild_reason, agent_name=agent_name)

        logger.info(
            {
                "event": "dynamic_graph_built",
                "nodes": list(self._nodes.keys()),
                "edges": self._edges,
                "graph_version": self._graph_version,
                "custom_agents": [n for n in self._nodes if n not in {
                    "start",
                    "intent",
                    "react",
                    "reasoning",
                    "supervisor",
                    "router",
                    "assemble",
                    "finalize",
                }],
            }
        )
        return compiled

    # ------------------------------------------------------------------
    # Node & edge helpers
    # ------------------------------------------------------------------

    def _add_core_nodes(self) -> None:
        self.add_node(StartNode(name="start"))
        self.add_node(IntentNode(name="intent"))
        self.add_node(ReActNode(name="react"))
        self.add_node(ReasoningNode(name="reasoning"))
        self.add_node(SupervisorNode(name="supervisor"))
        self.add_node(LoopControllerNode(name="loop_controller"))
        self.add_node(RouterNode(name="router"))

        self.add_node(CapiGusNode(name="capi_gus"))
        self.add_node(BranchNode(name="branch"))
        self.add_node(AnomalyNode(name="anomaly"))
        if _CAPI_NOTICIAS_AVAILABLE:
            self.add_node(CapiNoticiasNode(name="capi_noticias"))
        self.add_node(CapiDesktopNode(name="capi_desktop"))
        self.add_node(CapiDataBNode(name="capi_datab"))
        self.add_node(CapiElCajasNode(name="capi_elcajas"))
        self.add_node(CapiAlertasNode(name="capi_alertas"))
        self.add_node(HumanGateNode(name="human_gate"))
        self.add_node(AssembleNode(name="assemble"))
        self.add_node(FinalizeNode(name="finalize"))
        self._finish_node = "finalize"

    def _add_registered_agent_nodes(self) -> None:
        registered_agents = self.registry_service.list_registered_agents()
        for manifest in registered_agents:
            try:
                if not self.registry_service.config_service.is_enabled(manifest.agent_name):
                    logger.debug({
                        "event": "dynamic_agent_skipped",
                        "agent": manifest.agent_name,
                        "reason": "disabled",
                    })
                    continue
                node_instance = self._create_agent_node(manifest)
                if node_instance:
                    self.add_node(node_instance)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.error({
                    "event": "dynamic_agent_load_error",
                    "agent": manifest.agent_name,
                    "error": str(exc),
                })

    def _create_agent_node(self, manifest: AgentManifest) -> GraphNode | None:
        agent_name = manifest.agent_name
        if agent_name in self._node_cache:
            try:
                return self._node_cache[agent_name]()
            except Exception as exc:  # pragma: no cover
                logger.error({
                    "event": "dynamic_cache_instantiate_failed",
                    "agent": agent_name,
                    "error": str(exc),
                })

        node_path = (manifest.node_class_path or str(manifest.metadata.get("node_class_path", ""))).strip()
        if not node_path:
            logger.error({
                "event": "dynamic_agent_missing_path",
                "agent": agent_name,
            })
            return None

        try:
            module_name, class_name = node_path.rsplit(".", 1)
        except ValueError:
            logger.error({
                "event": "dynamic_agent_invalid_path",
                "agent": agent_name,
                "path": node_path,
            })
            return None

        try:
            module = importlib.import_module(module_name)
            AgentNode = getattr(module, class_name)
            node_instance: GraphNode = AgentNode(name=agent_name)
        except Exception as exc:  # pragma: no cover - observational logging
            logger.error({
                "event": "dynamic_agent_import_error",
                "agent": agent_name,
                "module": module_name,
                "class": class_name,
                "error": str(exc),
            })
            return None

        self._node_cache[agent_name] = AgentNode
        logger.info({
            "event": "dynamic_agent_loaded",
            "agent": agent_name,
            "module": module_name,
        })
        if not getattr(node_instance, "_is_agent_node", False):
            setattr(node_instance, "_is_agent_node", True)
        return node_instance

    def _setup_graph_edges(self) -> None:
        self.add_edge("start", "intent")
        self.add_edge("intent", "react")
        self.add_edge("react", "reasoning")
        self.add_edge("reasoning", "supervisor")
        self.add_edge("supervisor", "loop_controller")

        # FIX: Loop controller should have CONDITIONAL edge, not both edges
        # It should go to router OR assemble based on routing_decision
        def _loop_controller_resolver(state: GraphState) -> str:
            decision = getattr(state, "routing_decision", None)
            if decision == "assemble":
                return "assemble"
            elif decision and decision != "assemble":
                # Any other decision goes back to router
                return "router"
            else:
                # Default to assemble if no decision
                return "assemble"

        self.add_conditional_edges(
            "loop_controller",
            _loop_controller_resolver,
            {"router": "router", "assemble": "assemble"}
        )

        def _safe_add_edge(src: str, dst: str) -> None:
            if (src, dst) not in self._edges:
                self.add_edge(src, dst)

        built_in_agents = ["capi_gus", "branch", "anomaly", "capi_desktop", "summary"]
        if _CAPI_NOTICIAS_AVAILABLE:
            built_in_agents.append("capi_noticias")

        prioritized = {"capi_gus", "branch", "anomaly", "capi_desktop", "capi_datab", "capi_elcajas", "summary", "agente_g"}
        for agent_name in built_in_agents:
            if agent_name in self._nodes and self.registry_service.config_service.is_enabled(agent_name):
                _safe_add_edge(agent_name, "human_gate")
                if agent_name in prioritized:
                    _safe_add_edge(agent_name, "assemble")

        registered_agents = self.registry_service.list_registered_agents()
        for manifest in registered_agents:
            if self.registry_service.config_service.is_enabled(manifest.agent_name) and manifest.agent_name in self._nodes:
                _safe_add_edge(manifest.agent_name, "human_gate")
                if manifest.agent_name in prioritized:
                    _safe_add_edge(manifest.agent_name, "assemble")

        _safe_add_edge("human_gate", "assemble")
        if "capi_datab" in self._nodes:
            def _datab_router(state: GraphState) -> str:
                metadata = getattr(state, "response_metadata", {}) or {}
                if metadata.get("datab_alerts_pending"):
                    return "capi_alertas"
                if metadata.get("datab_desktop_ready"):
                    return "capi_desktop"
                if metadata.get("el_cajas_pending") or metadata.get("el_cajas_status") not in (None, "ok", "unknown"):
                    return "capi_elcajas"
                if metadata.get("datab_skip_human"):
                    return "assemble"
                return "human_gate"

            self.add_conditional_edges(
                "capi_datab",
                _datab_router,
                {
                    "capi_alertas": "capi_alertas",
                    "capi_desktop": "capi_desktop",
                    "capi_elcajas": "capi_elcajas",
                    "human_gate": "human_gate",
                    "assemble": "assemble",
                },
            )

        if "capi_alertas" in self._nodes:
            def _alertas_router(state: GraphState) -> str:
                metadata = getattr(state, "response_metadata", {}) or {}
                if metadata.get("desktop_instruction"):
                    return "capi_desktop"
                return "assemble"

            self.add_conditional_edges(
                "capi_alertas",
                _alertas_router,
                {
                    "capi_desktop": "capi_desktop",
                    "assemble": "assemble",
                },
            )
        _safe_add_edge("assemble", "finalize")

        available_targets = {
            name
            for name in self._nodes
            if name not in {"start", "intent", "react", "reasoning", "supervisor", "router"}
        }
        available_targets.add("assemble")

        def _router_resolver(state: GraphState) -> str | tuple[str, ...]:
            decision = getattr(state, "routing_decision", None)
            if isinstance(decision, (list, tuple)):
                valid = tuple(target for target in decision if target in available_targets)
                if valid:
                    return valid
            if decision and decision in available_targets:
                return decision
            metadata = getattr(state, "response_metadata", {}) or {}
            parallel = metadata.get("parallel_targets")
            if isinstance(parallel, (list, tuple)):
                valid_parallel = tuple(target for target in parallel if target in available_targets)
                if valid_parallel:
                    return valid_parallel
            active_agent = getattr(state, "active_agent", None)
            if active_agent and active_agent in available_targets:
                return active_agent
            return "assemble"

        path_map = {target: target for target in available_targets}
        self.add_conditional_edges("router", _router_resolver, path_map)

    # ------------------------------------------------------------------
    # Registry management helpers
    # ------------------------------------------------------------------

    def rebuild_with_new_agent(
        self,
        agent_name: str,
        *,
        checkpointer: BaseCheckpointSaver | None = None,
        interrupt_before: Iterable[str] | None = None,
    ) -> Any:
        logger.info({"event": "dynamic_graph_rebuild", "agent": agent_name})
        try:
            self.registry_service.refresh_registry()
        except Exception as exc:  # pragma: no cover - observational logging
            logger.error({"event": "dynamic_registry_refresh_error", "error": str(exc)})
        try:
            manifest = self.registry_service.get_agent_manifest(agent_name)
            desired_enabled = bool(getattr(manifest, "enabled", True)) if manifest else True
        except Exception as exc:  # pragma: no cover
            logger.error({"event": "dynamic_manifest_error", "agent": agent_name, "error": str(exc)})
            desired_enabled = True
        try:
            self.registry_service.config_service.set_enabled(agent_name, desired_enabled)
        except Exception as exc:  # pragma: no cover - observational logging
            logger.error({"event": "dynamic_config_set_error", "agent": agent_name, "error": str(exc)})
        return self.build_dynamic(
            rebuild_reason="register_agent",
            agent_name=agent_name,
            checkpointer=checkpointer or self._default_checkpointer,
            interrupt_before=interrupt_before or self._default_interrupts,
        )

    def remove_agent_from_graph(
        self,
        agent_name: str,
        *,
        checkpointer: BaseCheckpointSaver | None = None,
        interrupt_before: Iterable[str] | None = None,
    ) -> Any:
        logger.info({"event": "dynamic_graph_remove_agent", "agent": agent_name})
        try:
            self.registry_service.refresh_registry()
        except Exception as exc:  # pragma: no cover - observational logging
            logger.error({"event": "dynamic_registry_refresh_error", "error": str(exc)})
        try:
            self.registry_service.config_service.set_enabled(agent_name, False)
        except Exception as exc:  # pragma: no cover
            logger.warning({"event": "dynamic_disable_error", "agent": agent_name, "error": str(exc)})
        return self.build_dynamic(
            rebuild_reason="unregister_agent",
            agent_name=agent_name,
            checkpointer=checkpointer or self._default_checkpointer,
            interrupt_before=interrupt_before or self._default_interrupts,
        )

    def get_graph_info(self) -> Dict[str, Any]:
        if not self._last_build_info:
            return {
                "version": self._graph_version,
                "built_at": None,
                "entrypoint": self._entrypoint or "start",
                "node_count": len(self._nodes),
                "edge_count": len(self._edges),
                "nodes": sorted(self._nodes.keys()),
                "edges": list(self._edges),
                "registered_agents": [],
                "enabled_agents": [],
                "custom_agents": [],
                "rebuild_reason": None,
                "trigger_agent": None,
                "has_current_graph": self._last_compiled_graph is not None,
            }
        info = dict(self._last_build_info)
        info["has_current_graph"] = self._last_compiled_graph is not None
        return info

    def _capture_build_snapshot(self, rebuild_reason: str, agent_name: Optional[str]) -> None:
        try:
            status_list = self.registry_service.config_service.list_status()
            enabled_agents = sorted(status.name for status in status_list if status.enabled)
        except Exception as exc:  # pragma: no cover - observational logging
            logger.error({"event": "dynamic_status_error", "error": str(exc)})
            enabled_agents = []

        try:
            manifests = self.registry_service.list_registered_agents()
            registered_agents = sorted(manifest.agent_name for manifest in manifests)
        except Exception as exc:  # pragma: no cover - observational logging
            logger.error({"event": "dynamic_registered_error", "error": str(exc)})
            registered_agents = []

        custom_agents = sorted(agent for agent in registered_agents if agent not in self._core_agents)
        self._graph_version += 1
        self._last_build_info = {
            "version": self._graph_version,
            "built_at": datetime.utcnow().isoformat(),
            "entrypoint": self._entrypoint or "start",
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "nodes": sorted(self._nodes.keys()),
            "edges": list(self._edges),
            "registered_agents": registered_agents,
            "enabled_agents": enabled_agents,
            "custom_agents": custom_agents,
            "rebuild_reason": rebuild_reason,
            "trigger_agent": agent_name,
        }


class DynamicGraphManager:
    """Manager para controlar la construccion y reconstruccion dinÃ¡mica de grafos."""

    def __init__(
        self,
        registry_service: AgentRegistryService,
        *,
        checkpointer: BaseCheckpointSaver | None = None,
        interrupt_before: Iterable[str] | None = None,
    ) -> None:
        self.registry_service = registry_service
        self.current_graph: Any | None = None
        self._checkpointer = checkpointer
        self._interrupt_before = tuple(interrupt_before or ())
        self.builder = DynamicGraphBuilder(
            registry_service,
            checkpointer=checkpointer,
            interrupt_before=self._interrupt_before,
        )

    def initialize_graph(self) -> Any:
        self.current_graph = self.builder.build_dynamic(
            rebuild_reason="initialize",
            checkpointer=self._checkpointer,
            interrupt_before=self._interrupt_before,
        )
        return self.current_graph

    def register_agent_and_rebuild(self, agent_name: str) -> Any:
        self.current_graph = self.builder.rebuild_with_new_agent(
            agent_name,
            checkpointer=self._checkpointer,
            interrupt_before=self._interrupt_before,
        )
        return self.current_graph

    def unregister_agent_and_rebuild(self, agent_name: str) -> Any:
        self.current_graph = self.builder.remove_agent_from_graph(
            agent_name,
            checkpointer=self._checkpointer,
            interrupt_before=self._interrupt_before,
        )
        return self.current_graph

    def refresh_graph(self) -> Any:
        self.registry_service.refresh_registry()
        self.current_graph = self.builder.build_dynamic(
            rebuild_reason="manual_refresh",
            checkpointer=self._checkpointer,
            interrupt_before=self._interrupt_before,
        )
        return self.current_graph

    def get_current_graph(self) -> Any | None:
        return self.current_graph

    def get_graph_status(self) -> Dict[str, Any]:
        graph_info = self.builder.get_graph_info()
        registry_stats = self.registry_service.get_registry_stats()

        return {
            "graph": graph_info,
            "registry": registry_stats,
            "has_current_graph": self.current_graph is not None,
            "timestamp": datetime.now().isoformat(),
        }




