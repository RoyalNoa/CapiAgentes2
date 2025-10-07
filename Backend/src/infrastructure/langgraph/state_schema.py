"""
LangGraph State Schema and Mutators
- Centralized workflow state for LangGraph orchestrator
- Type-safe, JSON-serializable, with immutability-style helpers

Respects ARCHITECTURE.md: lives under infrastructure, consumes domain contracts.
"""
from __future__ import annotations

from typing import Annotated, Dict, Any, Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

# Domain contracts (do not modify)
from src.domain.contracts.intent import Intent
from src.domain.contracts.agent_io import AgentResult



# Reducers para campos constantes en ejecuciones paralelas
def _keep_constant(value: str, new_value: str) -> str:
    """Reducer de LangGraph: asegura valores constantes cuando hay caminos paralelos."""
    if value and new_value and value != new_value:
        raise ValueError(f"GraphState constant mismatch: {value!r} vs {new_value!r}")
    if not value:
        return new_value
    if not new_value:
        return value
    return value

ConstantStr = Annotated[str, _keep_constant]

class WorkflowStatus(str, Enum):
    INITIALIZED = "initialized"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class GraphState(BaseModel):
    # Core request context
    session_id: ConstantStr = Field(..., description="Unique session identifier")
    trace_id: ConstantStr = Field(..., description="Request tracing identifier")
    user_id: ConstantStr = Field(..., description="User identifier")
    original_query: str = Field(..., description="Original user query")
    workflow_mode: str = Field(default="chat", description="Workflow execution mode (chat, alert_monitor, etc.)")
    external_payload: Dict[str, Any] = Field(default_factory=dict, description="Raw payload for event-driven workflows")
    timestamp: datetime = Field(default_factory=datetime.now)

    # Workflow state
    status: WorkflowStatus = Field(default=WorkflowStatus.INITIALIZED)
    current_node: Optional[str] = Field(default=None)
    completed_nodes: List[str] = Field(default_factory=list)

    # Intent and routing
    detected_intent: Optional[Intent] = Field(default=None)
    intent_confidence: Optional[float] = Field(default=None)
    routing_decision: Optional[str] = Field(default=None)

    # Agent processing results
    agent_results: Dict[str, AgentResult] = Field(default_factory=dict)
    active_agent: Optional[str] = Field(default=None)

    # Memory and context
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list)
    memory_window: List[Dict[str, str]] = Field(default_factory=list)

    # Data and metrics
    financial_data_loaded: bool = Field(default=False)
    data_summary: Optional[Dict[str, Any]] = Field(default=None)
    processing_metrics: Dict[str, float] = Field(default_factory=dict)

    # Advanced reasoning
    reasoning_trace: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_summary: Optional[Dict[str, Any]] = Field(default=None)

    # Response construction
    response_message: Optional[str] = Field(default=None)
    response_data: Dict[str, Any] = Field(default_factory=dict)
    response_metadata: Dict[str, Any] = Field(default_factory=dict)
    shared_artifacts: Dict[str, Any] = Field(default_factory=dict)

    # Error handling
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)

    # Configuration (injected, read-only usage)
    config: Dict[str, Any] = Field(default_factory=dict)

    # Visualization (optional)
    graph_layout: Optional[str] = Field(default="hierarchical")
    node_positions: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    visualization_metadata: Dict[str, Any] = Field(default_factory=dict)
    last_frontend_update: Optional[datetime] = Field(default=None)
    frontend_subscriptions: List[str] = Field(default_factory=list)

    model_config = dict(arbitrary_types_allowed=True, extra='allow')

    def to_frontend_format(self) -> Dict[str, Any]:
        """Minimal transformation for frontend graph visualization."""
        return {
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "workflow_mode": self.workflow_mode,
            "status": self.status.value,
            "current_node": self.current_node,
            "completed_nodes": self.completed_nodes,
            "detected_intent": self.detected_intent.value if self.detected_intent else None,
            "agent_results": {
                k: (v.model_dump() if hasattr(v, "model_dump") else v.dict() if hasattr(v, "dict") else v)
                for k, v in self.agent_results.items()
            },
            "processing_metrics": self.processing_metrics,
            "reasoning_trace": self.reasoning_trace,
            "reasoning_summary": self.reasoning_summary,
            "errors": self.errors,
            "graph_layout": self.graph_layout,
            "node_positions": self.node_positions,
            "visualization_metadata": self.visualization_metadata,
            "external_payload": self.external_payload,
            "shared_artifacts": self.shared_artifacts,
        }


class StateMutator:
    """Immutable-style mutation helpers: return new GraphState instances."""

    @staticmethod
    def update_field(state: GraphState, field: str, value: Any) -> GraphState:
        data = state.model_dump()
        data[field] = value
        return GraphState(**data)

    @staticmethod
    def append_to_list(state: GraphState, field: str, value: Any) -> GraphState:
        data = state.model_dump()
        current = list(data.get(field, []))
        current.append(value)
        data[field] = current
        return GraphState(**data)

    @staticmethod
    def merge_dict(state: GraphState, field: str, values: Dict[str, Any]) -> GraphState:
        data = state.model_dump()
        current = dict(data.get(field, {}))
        current.update(values or {})
        data[field] = current
        return GraphState(**data)

    @staticmethod
    def add_error(state: GraphState, error_type: str, message: str, context: Optional[Dict[str, Any]] = None) -> GraphState:
        entry = {
            "error_type": error_type,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "context": context or {},
        }
        return StateMutator.append_to_list(state, "errors", entry)

    @staticmethod
    def increment_retry(state: GraphState) -> GraphState:
        return StateMutator.update_field(state, "retry_count", (state.retry_count or 0) + 1)

