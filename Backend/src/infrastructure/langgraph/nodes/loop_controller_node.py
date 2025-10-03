"""Loop controller node to coordinate iterative reasoning/react cycles."""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.core.logging import get_logger

logger = get_logger(__name__)


class LoopControllerNode(GraphNode):
    def __init__(self, name: str = "loop_controller", *, max_iterations: int = 3) -> None:
        super().__init__(name=name)
        self.max_iterations = max(1, max_iterations)

    def run(self, state: GraphState) -> GraphState:
        updated = StateMutator.update_field(state, "current_node", self.name)
        meta = dict(state.response_metadata or {})
        loop_info = meta.get("loop_controller", {})
        iteration = int(loop_info.get("iteration", 0)) + 1

        logger.debug({
            "event": "loop_controller_start",
            "iteration": iteration,
            "max": self.max_iterations,
            "reasoning_pending": meta.get("reasoning_needs_react"),
            "react_follow_up": meta.get("react_follow_up"),
            "needs_retry": meta.get("needs_retry"),
        })

        updated = StateMutator.merge_dict(
            updated,
            "response_metadata",
            {
                "loop_controller": {
                    "iteration": iteration,
                    "max": self.max_iterations,
                }
            },
        )

        if iteration > self.max_iterations:
            logger.info({
                "event": "loop_controller_max_reached",
                "iteration": iteration,
            })
            updated = StateMutator.update_field(updated, "routing_decision", "assemble")
            updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)
            return updated

        decision_override = self._handle_human_decision(updated)
        if decision_override is not None:
            updated, decision = decision_override
        else:
            meta = dict(updated.response_metadata or {})
            decision = self._resolve_next_step(meta)
            updated = StateMutator.update_field(updated, "routing_decision", decision)

        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        logger.debug({
            "event": "loop_controller_decision",
            "iteration": iteration,
            "next": decision,
        })
        return updated

    def _handle_human_decision(self, state: GraphState) -> Optional[Tuple[GraphState, str]]:
        meta = dict(state.response_metadata or {})
        decision = meta.get("human_decision")
        if not isinstance(decision, dict):
            return None
        if not meta.get("el_cajas_pending"):
            return None

        pending_instruction = meta.get("pending_desktop_instruction")
        metadata_updates: Dict[str, Any] = {
            "pending_desktop_instruction": None,
            "el_cajas_pending": False,
            "requires_human_approval": False,
        }

        if decision.get("approved") and pending_instruction:
            metadata_updates["desktop_instruction"] = pending_instruction
            metadata_updates["actions"] = []
            state = StateMutator.merge_dict(state, "response_metadata", metadata_updates)
            message_addition = "Procedo a generar la recomendación en el escritorio."
            current_message = (state.response_message or "").strip()
            new_message = f"{current_message}\n\n{message_addition}" if current_message else message_addition

            state = StateMutator.update_field(state, "response_message", new_message)
            state = StateMutator.update_field(state, "routing_decision", "capi_desktop")
            return state, "capi_desktop"

        metadata_updates["actions"] = []
        state = StateMutator.merge_dict(state, "response_metadata", metadata_updates)
        message_addition = "No guardaré la recomendación en el escritorio por pedido del usuario."
        current_message = (state.response_message or "").strip()
        new_message = f"{current_message}\n\n{message_addition}" if current_message else message_addition

        state = StateMutator.update_field(state, "response_message", new_message)
        state = StateMutator.update_field(state, "routing_decision", "assemble")
        return state, "assemble"

    def _resolve_next_step(self, meta: Dict[str, Any]) -> str:
        if meta.get("reasoning_needs_react"):
            return "react"
        if meta.get("react_follow_up"):
            return "reasoning"
        retry_target = meta.get("needs_retry")
        if isinstance(retry_target, str) and retry_target:
            return retry_target
        return meta.get("active_agent") or "assemble"

__all__ = ["LoopControllerNode"]


