
"""Supervisor pattern node that coordinates specialized agents based on planning metadata."""
from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, Iterable, List, Optional

from src.core.logging import get_logger
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator

logger = get_logger(__name__)


class SupervisorNode(GraphNode):
    """Decides the execution queue for downstream agent nodes."""

    def __init__(self, name: str = "supervisor", *, default_queue: Optional[Iterable[str]] = None) -> None:
        super().__init__(name=name)
        self._default_queue = list(default_queue) if default_queue is not None else [
            "summary",
            "anomaly",
            "capi_desktop",
            "capi_gus",
        ]

    def run(self, state: GraphState) -> GraphState:
        start = time.time()
        logger.debug({"event": "supervisor_node_start", "session_id": state.session_id})

        updated = StateMutator.update_field(state, "current_node", self.name)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        metadata = dict(updated.response_metadata or {})
        plan = metadata.get("reasoning_plan") or {}
        cooperative = list(plan.get("cooperative_agents") or [])
        recommended = plan.get("recommended_agent")

        react_agent = metadata.get("react_recommended_agent")
        prior_queue = metadata.get("supervisor_queue") or []

        queue_candidates: List[str] = []
        if react_agent:
            queue_candidates.append(str(react_agent))
        if recommended:
            queue_candidates.append(str(recommended))
        queue_candidates.extend(str(agent) for agent in cooperative if agent)
        queue_candidates.extend(str(agent) for agent in prior_queue if agent)
        queue_candidates.extend(self._default_queue)

        queue: List[str] = []
        for candidate in queue_candidates:
            if candidate and candidate not in queue:
                queue.append(candidate)

        next_agent = queue[0] if queue else None
        if not next_agent:
            logger.warning({"event": "supervisor_no_agent", "session_id": state.session_id})

        updated = StateMutator.merge_dict(
            updated,
            "response_metadata",
            {
                "supervisor_queue": queue,
                "supervisor_selected": next_agent,
                "supervisor_ran_at": datetime.now().isoformat(),
            },
        )

        if next_agent:
            updated = StateMutator.update_field(updated, "routing_decision", next_agent)
            updated = StateMutator.update_field(updated, "active_agent", next_agent)

        duration_ms = int((time.time() - start) * 1000)
        updated = StateMutator.merge_dict(
            updated,
            "processing_metrics",
            {
                "supervisor_latency_ms": duration_ms,
                "supervisor_queue_length": len(queue),
            },
        )

        updated = StateMutator.append_to_list(
            updated,
            "reasoning_trace",
            {
                "type": "supervisor",
                "queue": queue,
                "selected_agent": next_agent,
                "timestamp": datetime.now().isoformat(),
            },
        )

        logger.info({
            "event": "supervisor_node_end",
            "session_id": state.session_id,
            "next_agent": next_agent,
            "queue_length": len(queue),
            "duration_ms": duration_ms,
        })
        return updated


__all__ = ["SupervisorNode"]

