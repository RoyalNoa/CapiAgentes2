"""
LangGraph builder: constructs a LangGraph StateGraph using our domain nodes.
Expands later with intent, agent subgraphs, and conditional routing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

from langgraph.graph import StateGraph
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver

from src.core.logging import get_logger
from src.infrastructure.langgraph.state_schema import GraphState
from src.infrastructure.langgraph.nodes.base import GraphNode, StartNode, FinalizeNode
from src.infrastructure.langgraph.nodes.intent_node import IntentNode
from src.infrastructure.langgraph.nodes.react_node import ReActNode
from src.infrastructure.langgraph.nodes.reasoning_node import ReasoningNode
from src.infrastructure.langgraph.nodes.supervisor_node import SupervisorNode
from src.infrastructure.langgraph.nodes.loop_controller_node import LoopControllerNode
from src.infrastructure.langgraph.nodes.router_node import RouterNode
from src.infrastructure.langgraph.nodes.capi_gus_node import CapiGusNode
from src.infrastructure.langgraph.nodes.branch_node import BranchNode
from src.infrastructure.langgraph.nodes.anomaly_node import AnomalyNode
from src.infrastructure.langgraph.nodes.capi_desktop_node import CapiDesktopNode
from src.infrastructure.langgraph.nodes.capi_datab_node import CapiDataBNode
from src.infrastructure.langgraph.nodes.capi_elcajas_node import CapiElCajasNode
try:
        _AGENTE_G_AVAILABLE = True
except ImportError:
    AgenteGNode = None
    _AGENTE_G_AVAILABLE = False
from src.infrastructure.langgraph.nodes.agente_g_node import AgenteGNode
from src.infrastructure.langgraph.nodes.human_gate_node import HumanGateNode
try:
    from src.infrastructure.langgraph.nodes.capi_noticias_node import CapiNoticiasNode
    _CAPI_NOTICIAS_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    _CAPI_NOTICIAS_AVAILABLE = False
from src.infrastructure.langgraph.nodes.assemble_node import AssembleNode

logger = get_logger(__name__)


@dataclass
class ConditionalEdge:
    resolver: Callable[[GraphState], str]
    path_map: Dict[str, str]


class GraphBuilder:
    def __init__(self) -> None:
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: List[Tuple[str, str]] = []
        self._conditional_edges: Dict[str, ConditionalEdge] = {}
        self._entrypoint: Optional[str] = None
        self._finish_node: Optional[str] = None
        self._last_metadata: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add_node(self, node: GraphNode) -> "GraphBuilder":
        self._nodes[node.name] = node
        if self._entrypoint is None:
            self._entrypoint = node.name
        return self

    def add_edge(self, src: str, dst: str) -> "GraphBuilder":
        if (src, dst) not in self._edges:
            self._edges.append((src, dst))
        return self

    def add_conditional_edges(
        self,
        source: str,
        resolver: Callable[[GraphState], str],
        path_map: Dict[str, str],
    ) -> "GraphBuilder":
        self._conditional_edges[source] = ConditionalEdge(resolver=resolver, path_map=path_map)
        return self

    def reset(self) -> None:
        self._nodes.clear()
        self._edges.clear()
        self._conditional_edges.clear()
        self._entrypoint = None
        self._finish_node = None

    def build_minimal(
        self,
        *,
        checkpointer: Optional[BaseCheckpointSaver] = None,
        interrupt_before: Optional[Iterable[str]] = None,
    ):
        """Build minimal graph with LangGraph StateGraph backend."""
        self.reset()

        # Core workflow nodes
        self.add_node(StartNode(name="start"))
        self.add_node(IntentNode(name="intent"))
        self.add_node(ReActNode(name="react"))
        self.add_node(ReasoningNode(name="reasoning"))
        self.add_node(SupervisorNode(name="supervisor"))
        self.add_node(LoopControllerNode(name="loop_controller"))
        self.add_node(RouterNode(name="router"))

        # Agent / specialized nodes
        self.add_node(CapiGusNode(name="capi_gus"))
        self.add_node(BranchNode(name="branch"))
        self.add_node(AnomalyNode(name="anomaly"))
        if _CAPI_NOTICIAS_AVAILABLE:
            self.add_node(CapiNoticiasNode(name="capi_noticias"))
        self.add_node(CapiDesktopNode(name="capi_desktop"))
        self.add_node(CapiDataBNode(name="capi_datab"))
        self.add_node(CapiElCajasNode(name="capi_elcajas"))
        if _AGENTE_G_AVAILABLE:
            self.add_node(AgenteGNode(name="agente_g"))
        self.add_node(HumanGateNode(name="human_gate"))
        self.add_node(AssembleNode(name="assemble"))
        self.add_node(FinalizeNode(name="finalize"))
        self._finish_node = "finalize"

        # Linear workflow edges
        self.add_edge("start", "intent")
        self.add_edge("intent", "react")
        self.add_edge("react", "reasoning")
        self.add_edge("reasoning", "supervisor")
        self.add_edge("supervisor", "loop_controller")

        # FIX: Loop controller should have CONDITIONAL edge
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

        # Router conditional routing
        available_targets = {
            name
            for name in (
                "capi_gus",
                "branch",
                "anomaly",
                "capi_desktop",
                "capi_datab",
                "capi_elcajas",
                "capi_noticias",
                "assemble",
            )
            if name in self._nodes
        }
        if _AGENTE_G_AVAILABLE and "agente_g" in self._nodes:
            available_targets.add("agente_g")
        if "assemble" not in available_targets:
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
            if not isinstance(metadata, dict):
                metadata = {}
            recommended_agent = metadata.get("recommended_agent")
            if recommended_agent and recommended_agent in available_targets:
                return recommended_agent
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

        # Directed edges from agent nodes to assemble/finalize
        if "capi_datab" in self._nodes:
            alertas_available = "capi_alertas" in self._nodes

            def _datab_router(state: GraphState) -> str:
                metadata = getattr(state, "response_metadata", None)
                if metadata is None and isinstance(state, dict):
                    metadata = state.get("response_metadata")
                if hasattr(metadata, "model_dump"):
                    metadata = metadata.model_dump()
                metadata = metadata or {}

                shared = getattr(state, "shared_artifacts", None)
                if shared is None and isinstance(state, dict):
                    shared = state.get("shared_artifacts")
                if hasattr(shared, "model_dump"):
                    shared = shared.model_dump()
                datab_bucket = shared.get("capi_datab") if isinstance(shared, dict) else None
                has_rows = False
                if isinstance(datab_bucket, dict):
                    rows = datab_bucket.get("rows")
                    if isinstance(rows, list) and rows:
                        has_rows = True

                if alertas_available and metadata.get("datab_alerts_pending"):
                    return "capi_alertas"
                if has_rows or metadata.get("el_cajas_pending") or metadata.get("el_cajas_status") not in (None, "ok", "unknown"):
                    return "capi_elcajas"
                if metadata.get("datab_desktop_ready"):
                    return "capi_desktop"
                if metadata.get("datab_skip_human"):
                    return "assemble"
                return "human_gate"

            path_map = {
                "capi_alertas": "capi_alertas",
                "capi_desktop": "capi_desktop",
                "capi_elcajas": "capi_elcajas",
                "human_gate": "human_gate",
                "capi_gus": "capi_gus",
                "assemble": "assemble",
            }
            if not alertas_available:
                path_map.pop("capi_alertas")

            self.add_conditional_edges("capi_datab", _datab_router, path_map)
        for agent_name in list(available_targets):
            if agent_name in {"assemble", "finalize", "capi_elcajas", "capi_gus"}:
                continue
            if agent_name == "capi_datab":
                continue
            if agent_name in self._nodes:
                self.add_edge(agent_name, "human_gate")
        if "capi_elcajas" in self._nodes and "capi_gus" in self._nodes:
            self.add_edge("capi_elcajas", "capi_gus")
        if "capi_gus" in self._nodes:
            self.add_edge("capi_gus", "human_gate")
        self.add_edge("human_gate", "assemble")
        self.add_edge("assemble", "finalize")

        compiled = self._compile_state_graph(
            checkpointer=checkpointer,
            interrupt_before=interrupt_before,
        )

        logger.info(
            {
                "event": "graph_built",
                "nodes": list(self._nodes.keys()),
                "edges": self._edges,
                "entrypoint": self._entrypoint,
            }
        )
        return compiled

    def get_graph_metadata(self) -> Dict[str, Any]:
        return {
            "entrypoint": self._entrypoint,
            "finish_node": self._finish_node,
            "nodes": sorted(self._nodes.keys()),
            "edge_count": len(self._edges),
            "edges": list(self._edges),
            "conditional": {k: list(v.path_map.keys()) for k, v in self._conditional_edges.items()},
            "last_compile": dict(self._last_metadata),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _wrap_node(node: GraphNode) -> Callable[[GraphState], GraphState]:
        def _runner(state: GraphState) -> GraphState:
            return node.run(state)

        return _runner

    def _compile_state_graph(
        self,
        *,
        checkpointer: Optional[BaseCheckpointSaver],
        interrupt_before: Optional[Iterable[str]],
    ):
        if not self._entrypoint:
            raise ValueError("Graph entrypoint not defined before compilation")

        workflow = StateGraph(GraphState)
        for node in self._nodes.values():
            workflow.add_node(node.name, self._wrap_node(node))

        workflow.set_entry_point(self._entrypoint)
        if self._finish_node and self._finish_node in self._nodes:
            workflow.set_finish_point(self._finish_node)

        for src, dst in self._edges:
            workflow.add_edge(src, dst)

        for source, conditional in self._conditional_edges.items():
            if source not in self._nodes:
                logger.warning({"event": "conditional_source_missing", "source": source})
                continue
            workflow.add_conditional_edges(source, conditional.resolver, conditional.path_map)

        compiled = workflow.compile(
            checkpointer=checkpointer or MemorySaver(),
            interrupt_before=tuple(interrupt_before or ()),
        )

        self._last_metadata = {
            "node_count": len(self._nodes),
            "edge_count": len(self._edges),
            "conditional_nodes": list(self._conditional_edges.keys()),
        }
        return compiled


