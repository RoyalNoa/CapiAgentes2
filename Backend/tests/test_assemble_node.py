from datetime import datetime

from src.domain.contracts.intent import Intent
from src.infrastructure.langgraph.nodes.assemble_node import AssembleNode
from src.infrastructure.langgraph.state_schema import GraphState, WorkflowStatus


def _make_state(**overrides) -> GraphState:
    base = dict(
        session_id="session-x",
        trace_id="trace-x",
        user_id="user-x",
        original_query="consulta sin datos",
        workflow_mode="chat",
        external_payload={},
        timestamp=datetime.utcnow(),
        detected_intent=Intent.UNKNOWN,
        intent_confidence=0.1,
        response_message=None,
        response_metadata={},
        completed_nodes=[],
        status=WorkflowStatus.INITIALIZED,
    )
    base.update(overrides)
    return GraphState(**base)


def test_assemble_node_produces_capi_gus_fallback():
    state = _make_state()
    node = AssembleNode()

    result = node.run(state)

    assert result.response_message is not None
    assert "Capi Gus" in result.response_message
    assert result.active_agent == "capi_gus"
    meta = result.response_metadata or {}
    assert meta.get("active_agent") == "capi_gus"
    assert meta.get("capi_gus_fallback") is True
