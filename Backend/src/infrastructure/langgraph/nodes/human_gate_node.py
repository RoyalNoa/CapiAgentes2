"""
HumanGateNode: Pausa el flujo hasta obtener aprobacion humana cuando una operaciÃƒÂ³n sensible lo requiere.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from langgraph.types import Command, interrupt

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator, WorkflowStatus
from src.core.logging import get_logger

logger = get_logger(__name__)


class HumanGateNode(GraphNode):
    def __init__(self, name: str = "human_gate") -> None:
        super().__init__(name=name)
        self._is_agent_node = False

    def run(self, state: GraphState) -> GraphState:
        logger.debug({"event": "human_gate_start", "session_id": state.session_id})
        requires_review, context = self._needs_human_review(state)
        updated = StateMutator.update_field(state, "current_node", self.name)

        if not requires_review:
            return StateMutator.append_to_list(updated, "completed_nodes", self.name)

        decision: Optional[Dict[str, Any]] = self._extract_decision(state)
        if decision is None:
            logger.info({
                "event": "human_gate_interrupt",
                "session_id": state.session_id,
                "trace_id": state.trace_id,
                "reason": context.get("reason"),
            })
            decision = interrupt(
                {
                    "node": self.name,
                    "session_id": state.session_id,
                    "trace_id": state.trace_id,
                    "context": context,
                }
            )

        approved = bool(decision.get("approved", False))
        metadata_updates = {
            "human_decision": decision,
            "human_approved": approved,
        }
        updated = StateMutator.merge_dict(updated, "response_metadata", metadata_updates)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        if approved:
            logger.info({
                "event": "human_gate_approved",
                "session_id": state.session_id,
                "trace_id": state.trace_id,
            })
            return updated

        logger.info({
            "event": "human_gate_rejected",
            "session_id": state.session_id,
            "trace_id": state.trace_id,
        })
        updated = StateMutator.update_field(
            updated,
            "status",
            WorkflowStatus.PAUSED,
        )
        rejection_message = decision.get("message") or "Accion detenida hasta obtener aprobacion humana."
        updated = StateMutator.update_field(updated, "response_message", rejection_message)
        updated = StateMutator.merge_dict(
            updated,
            "response_metadata",
            {"human_blocked": True},
        )
        return updated

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _needs_human_review(self, state: GraphState) -> tuple[bool, Dict[str, Any]]:
        metadata = state.response_metadata or {}
        semantic_action = metadata.get("semantic_action")
        requires_flag = metadata.get("requires_human_approval")
        sensitive = semantic_action in {"WRITE_FILE", "MODIFY_FILE", "DELETE"}
        requires_review = bool(requires_flag or sensitive)
        context = {
            "reason": metadata.get("approval_reason")
            or "Se requiere aprobacion antes de ejecutar operaciones de escritura.",
            "semantic_action": semantic_action,
            "metadata": {k: v for k, v in metadata.items() if k not in {"human_decision"}},
        }
        return requires_review, context

    def _extract_decision(self, state: GraphState) -> Optional[Dict[str, Any]]:
        metadata = state.response_metadata or {}
        decision = metadata.get("human_decision")
        if isinstance(decision, dict):
            return decision
        return None
