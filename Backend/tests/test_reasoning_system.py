import os
import pytest

os.environ.setdefault("SECRET_KEY", "test_secret_key_for_reasoner_1234567890123456")
os.environ.setdefault("API_KEY_BACKEND", "test_api_key_backend_1234")

from src.infrastructure.langgraph.nodes.reasoning_node import ReasoningNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.domain.contracts.intent import Intent


def _base_state(query: str) -> GraphState:
    return GraphState(
        session_id="test_session",
        trace_id="trace-123",
        user_id="user-123",
        original_query=query,
    )


def test_reasoning_node_generates_plan_for_summary():
    node = ReasoningNode()
    node._reasoner.config_service.set_enabled("capi_gus", True)
    state = _base_state("Necesito un resumen ejecutivo de los datos financieros del mes")
    state = StateMutator.update_field(state, "detected_intent", Intent.SUMMARY_REQUEST)

    result = node.run(state)

    plan = result.response_metadata.get("reasoning_plan")
    assert plan is not None, "Reasoning plan should be generated"
    assert plan["recommended_agent"] in {"capi_gus", "summary", "capi_desktop"}
    assert plan["goal"]
    assert plan["version"] == 1
    assert plan["plan_id"]
    assert plan["remaining_steps"] == len(plan.get("steps", []))
    assert plan["estimated_effort_seconds"] >= len(plan.get("steps", []))
    assert plan["progress_percent"] >= 10
    assert plan["complexity"] in {"low", "medium", "high"}
    metrics = result.processing_metrics
    assert metrics.get("reasoning_progress_percent") is not None
    assert metrics.get("reasoning_eta_seconds") >= plan["estimated_effort_seconds"]
    assert result.reasoning_trace, "Reasoning trace should capture plan metadata"
    assert result.response_data.get("reasoning_plan") == plan
    summary = result.reasoning_summary
    assert summary
    assert summary.get("complexity") == plan["complexity"]


def test_reasoning_node_generates_plan_for_file_operation():
    node = ReasoningNode()
    node._reasoner.config_service.set_enabled("capi_gus", True)
    state = _base_state("Muéstrame qué contiene el archivo ventas_actuales.xlsx")
    state = StateMutator.update_field(state, "detected_intent", Intent.FILE_OPERATION)

    result = node.run(state)

    plan = result.response_metadata.get("reasoning_plan")
    assert plan is not None
    assert plan["recommended_agent"] == "capi_desktop"
    assert any(step["agent"] == "capi_desktop" for step in plan["steps"])
    assert plan["cooperative_agents"], "File operations should involve cooperative agents"
    assert plan["estimated_effort_seconds"] >= len(plan["steps"])
    assert plan["progress_percent"] >= 10


def test_reasoning_node_replans_when_agent_disabled():
    node = ReasoningNode()
    node._reasoner.config_service.set_enabled("capi_gus", True)
    state = _base_state("Hola, puedes resumir los datos?")
    state = StateMutator.update_field(state, "detected_intent", Intent.SUMMARY_REQUEST)

    first_result = node.run(state)
    first_plan = first_result.response_metadata["reasoning_plan"]
    plan_id = first_plan["plan_id"]

    # Disable summary agent to force replan and inject an error signal
    node._reasoner.config_service.set_enabled("capi_gus", False)
    errored_state = StateMutator.append_to_list(first_result, "errors", {"type": "agent_failure"})

    second_result = node.run(errored_state)
    second_plan = second_result.response_metadata["reasoning_plan"]

    assert second_plan["plan_id"] == plan_id, "Replan should reuse same plan id"
    assert second_plan["version"] == first_plan["version"] + 1
    assert second_plan["recommended_agent"] != first_plan["recommended_agent"]
    assert second_plan["history"], "Replan should keep history of previous versions"

    # Restore summary agent for downstream suites
    node._reasoner.config_service.set_enabled("capi_gus", True)


def test_reasoning_node_handles_empty_query_gracefully():
    node = ReasoningNode()
    state = _base_state("")

    result = node.run(state)

    assert not result.reasoning_trace
    assert "reasoning_plan" not in result.response_metadata
    assert result.processing_metrics.get("reasoning_time_ms") >= 0
