"""Node that performs advanced reasoning before routing."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.application.reasoning.advanced_reasoner import AdvancedReasoner, ReasoningPlan
from src.core.logging import get_logger

logger = get_logger(__name__)


class ReasoningNode(GraphNode):
    """Deliberation node that prepares a multi-step plan for downstream agents."""

    def __init__(self, name: str = "reasoning") -> None:
        super().__init__(name=name)
        self._reasoner = AdvancedReasoner()

    def run(self, state: GraphState) -> GraphState:
        start_time = time.time()
        user_query = getattr(state, "user_query", None)
        query = state.original_query or user_query or ""

        logger.info(
            {
                "event": "reasoning_node_start",
                "node": self.name,
                "query_preview": (query[:120] + "...") if len(query) > 120 else query,
            }
        )

        if not query:
            logger.info({"event": "reasoning_node_skip", "reason": "empty_query"})
            updated = self._finalize_state(state, None, start_time, plan_changed=False)
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {"reasoning_needs_react": False},
            )
            return updated

        previous_plan_dict: Optional[Dict[str, Any]] = None
        if state.response_metadata:
            previous_plan_dict = state.response_metadata.get("reasoning_plan")

        plan_changed = False
        plan: Optional[ReasoningPlan] = None

        if previous_plan_dict:
            previous_plan = ReasoningPlan.from_dict(previous_plan_dict)
            if self._reasoner.needs_replan(previous_plan, state):
                plan = self._reasoner.replan_from_state(
                    previous_plan,
                    query=query,
                    session_id=state.session_id,
                    user_id=state.user_id,
                    state=state,
                )
                plan_changed = True
            else:
                plan = previous_plan
        else:
            plan = self._reasoner.generate_plan(
                query=query,
                session_id=state.session_id,
                user_id=state.user_id,
                intent_hint=state.detected_intent,
            )
            plan_changed = True

        new_state = self._finalize_state(state, plan, start_time, plan_changed=plan_changed)
        needs_react = bool(plan and plan.remaining_steps and plan.recommended_agent)
        new_state = StateMutator.merge_dict(
            new_state,
            "response_metadata",
            {
                "reasoning_needs_react": needs_react,
                "loop_fallback": plan.recommended_agent if plan else None,
            },
        )
        return new_state

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _finalize_state(
        self,
        state: GraphState,
        plan: ReasoningPlan | None,
        start_time: float,
        *,
        plan_changed: bool,
    ) -> GraphState:
        updated = StateMutator.update_field(state, "current_node", self.name)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        reasoning_metrics: Dict[str, Any] = {
            "reasoning_time_ms": int((time.time() - start_time) * 1000),
        }

        if plan is not None:
            plan_dict = plan.to_dict()
            updated = StateMutator.merge_dict(
                updated,
                "response_metadata",
                {
                    "reasoning_plan": plan_dict,
                    "reasoning_confidence": plan_dict.get("confidence"),
                    "recommended_agent": plan_dict.get("recommended_agent"),
                    "reasoning_progress_percent": plan.progress_percent,
                    "reasoning_eta_seconds": plan.estimated_effort_seconds,
                    "reasoning_remaining_steps": plan.remaining_steps,
                    "reasoning_complexity": plan.complexity,
                },
            )
            updated = StateMutator.merge_dict(
                updated,
                "response_data",
                {"reasoning_plan": plan_dict},
            )

            existing_trace_versions = {
                entry.get("version") for entry in (updated.reasoning_trace or [])
            }
            if plan.version not in existing_trace_versions:
                updated = StateMutator.append_to_list(
                    updated,
                    "reasoning_trace",
                    plan.to_trace_entry(),
                )
            elif plan_changed:
                # replace last entry if version already tracked but plan changed
                trace = list(updated.reasoning_trace)
                trace = [entry for entry in trace if entry.get("version") != plan.version]
                trace.append(plan.to_trace_entry())
                updated = StateMutator.update_field(updated, "reasoning_trace", trace)

            remaining_percent = max(0.0, 100.0 - plan.progress_percent)
            updated = StateMutator.update_field(
                updated,
                "reasoning_summary",
                {
                    "goal": plan.goal,
                    "recommended_agent": plan.recommended_agent,
                    "confidence": plan.confidence,
                    "version": plan.version,
                    "cooperative_agents": plan.cooperative_agents,
                    "progress_percent": plan.progress_percent,
                    "remaining_steps": plan.remaining_steps,
                    "complexity": plan.complexity,
                    "estimated_effort_seconds": plan.estimated_effort_seconds,
                    "remaining_percent": round(remaining_percent, 1),
                },
            )
            reasoning_metrics["reasoning_steps"] = len(plan.steps)
            reasoning_metrics["reasoning_version"] = plan.version
            reasoning_metrics["reasoning_progress_percent"] = plan.progress_percent
            reasoning_metrics["reasoning_eta_seconds"] = plan.estimated_effort_seconds
            reasoning_metrics["reasoning_remaining_steps"] = plan.remaining_steps

        updated = StateMutator.merge_dict(
            updated, "processing_metrics", reasoning_metrics
        )

        logger.info(
            {
                "event": "reasoning_node_end",
                "plan_generated": plan is not None,
                "plan_changed": plan_changed,
                "recommended_agent": plan.recommended_agent if plan else None,
                "duration_ms": reasoning_metrics["reasoning_time_ms"],
            }
        )
        return updated

__all__ = ["ReasoningNode"]


