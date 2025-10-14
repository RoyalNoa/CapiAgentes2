"""
Nodo responsable de enrutar la conversaciÃƒÆ’Ã‚Â³n al agente adecuado apoyÃƒÆ’Ã‚Â¡ndose en el
servicio semÃƒÆ’Ã‚Â¡ntico basado en LLM.
"""
from __future__ import annotations

import time
from typing import Optional

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.domain.contracts.intent import Intent
from src.core.logging import get_logger
from src.application.services.agent_config_service import AgentConfigService
from src.shared.agent_config_repository import FileAgentConfigRepository
from src.core.semantics import SemanticIntentService, get_global_context_manager
from src.core.feature_flags import is_semantic_nlp_enabled
from src.core.monitoring import get_semantic_metrics

logger = get_logger(__name__)


class RouterNode(GraphNode):
    def __init__(self, name: str = "router") -> None:
        super().__init__(name=name)
        self._agent_repo = FileAgentConfigRepository()
        self._agent_service = AgentConfigService(self._agent_repo)
        self.semantic_service = SemanticIntentService()
        self.context_manager = get_global_context_manager()
        self.metrics = get_semantic_metrics()

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "router_node_start", "node": self.name})

        metadata_snapshot = dict(state.response_metadata or {})
        completed_nodes = list(state.completed_nodes or [])
        if "capi_datab" in completed_nodes and "capi_gus" not in completed_nodes:
            target_agent: Optional[str] = None
            if metadata_snapshot.get("el_cajas_pending") or metadata_snapshot.get("el_cajas_status") not in (None, "ok", "unknown"):
                target_agent = "capi_elcajas"
            elif metadata_snapshot.get("datab_desktop_ready"):
                target_agent = "capi_desktop"
            elif metadata_snapshot.get("datab_skip_human"):
                target_agent = "assemble"
            if target_agent is None:
                target_agent = "capi_gus"

            if target_agent and target_agent not in completed_nodes:
                logger.info({"event": "router_short_circuit", "from": "capi_datab", "target": target_agent})
                intent = state.detected_intent or Intent.UNKNOWN
                confidence = state.intent_confidence or 0.0
                return self._finalize_route(state, target_agent=target_agent, intent=intent, confidence=confidence)

        query = state.original_query or state.user_query or ""
        if not query.strip():
            return self._finalize_route(state, target_agent="assemble", intent=Intent.UNKNOWN, confidence=0.0)

        start_time = time.time()
        use_semantic = is_semantic_nlp_enabled(state.session_id)

        if use_semantic:
            context = self.context_manager.get_context_summary(state.session_id)
            context.update({"session_id": state.session_id, "trace_id": state.trace_id})
            result = self.semantic_service.classify_intent(query, context)
        else:
            # Feature flag disabled -> minimal deterministic fallback
            result = self.semantic_service._fallback_result(query=query, reason="feature_flag_disabled")

        processing_time_ms = max((time.time() - start_time) * 1000, 0.1)
        routing_agent = self._select_enabled_agent(result.target_agent, result.intent)

        logger.info(
            {
                "event": "router_decision",
                "intent": result.intent.value,
                "target_agent": routing_agent,
                "confidence": result.confidence,
                "requires_clarification": result.requires_clarification,
                "processing_time_ms": processing_time_ms,
            }
        )

        self.metrics.track_intent_classification(
            session_id=state.session_id,
            query=query,
            predicted_intent=result.intent,
            confidence=result.confidence,
            processing_time_ms=processing_time_ms,
            system_used="semantic" if use_semantic else "fallback",
        )

        metadata = dict(state.response_metadata or {})
        metadata.update(
            {
                "semantic_result": {
                    "intent": result.intent.value,
                    "confidence": result.confidence,
                    "target_agent": result.target_agent,
                    "routing_agent": routing_agent,
                    "entities": result.entities,
                    "reasoning": result.reasoning,
                    "requires_clarification": result.requires_clarification,
                    "provider": result.provider,
                    "model": result.model,
                }
            }
        )
        updated_state = StateMutator.merge_dict(state, "response_metadata", metadata)
        updated_state = StateMutator.update_field(updated_state, "detected_intent", result.intent)
        updated_state = StateMutator.update_field(updated_state, "intent_confidence", result.confidence)
        updated_state = StateMutator.update_field(updated_state, "routing_decision", routing_agent)
        updated_state = StateMutator.append_to_list(updated_state, "completed_nodes", self.name)

        return updated_state

    def _select_enabled_agent(self, suggested: str, intent: Intent) -> str:
        candidates = []
        suggested = (suggested or "").strip().lower()
        if suggested == "smalltalk":
            suggested = "capi_gus"
        if suggested:
            candidates.append(suggested)

        default_agent = self.semantic_service._select_agent(intent, None)
        if default_agent == "smalltalk":
            default_agent = "capi_gus"
        if default_agent not in candidates:
            candidates.append(default_agent)

        candidates.extend(["capi_gus", "capi_datab", "capi_desktop", "agente_g", "assemble", "summary"])

        for agent in candidates:
            if agent and self._agent_service.is_enabled(agent):
                return agent
        return "assemble"

    def _finalize_route(self, state: GraphState, *, target_agent: str, intent: Intent, confidence: float) -> GraphState:
        updated = StateMutator.update_field(state, "routing_decision", target_agent)
        updated = StateMutator.update_field(updated, "detected_intent", intent)
        updated = StateMutator.update_field(updated, "intent_confidence", confidence)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
        return updated


__all__ = ["RouterNode"]
