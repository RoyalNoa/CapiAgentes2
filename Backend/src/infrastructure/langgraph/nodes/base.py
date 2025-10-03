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
        """Schedule broadcaster coroutine regardless of loop context."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:  # No running loop -> safe to run synchronously
            try:
                asyncio.run(coro)
            except Exception as exc:  # pragma: no cover - defensive logging
                logger.warning(f"Failed to emit {description}: {exc}")
        else:
            task = loop.create_task(coro)

            def _log_task_failure(task: asyncio.Task) -> None:
                with suppress(asyncio.CancelledError):
                    exc = task.exception()
                if exc:
                    logger.warning(f"Failed to emit {description}: {exc}")

            task.add_done_callback(_log_task_failure)

    def _emit_agent_start(self, state: GraphState):
        """EXPERT INTEGRATION: Emit WebSocket event when agent starts."""
        if hasattr(self, "_is_agent_node") and self._is_agent_node:
            broadcaster = get_event_broadcaster()
            self._emit_async_event(
                broadcaster.broadcast_agent_start(
                    agent_name=self.name,
                    session_id=state.session_id or "unknown",
                    meta={"trace_id": state.trace_id, "node": self.name}
                ),
                "agent_start event"
            )

    def _emit_agent_end(self, state: GraphState, success: bool = True, duration_ms: Optional[float] = None):
        """EXPERT INTEGRATION: Emit WebSocket event when agent ends."""
        if hasattr(self, "_is_agent_node") and self._is_agent_node:
            broadcaster = get_event_broadcaster()
            self._emit_async_event(
                broadcaster.broadcast_agent_end(
                    agent_name=self.name,
                    session_id=state.session_id or "unknown",
                    success=success,
                    duration_ms=duration_ms,
                    meta={"trace_id": state.trace_id, "node": self.name}
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
