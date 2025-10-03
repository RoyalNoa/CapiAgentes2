from datetime import datetime

import pytest

from src.domain.agents.agent_models import AgentResult, TaskStatus
from src.infrastructure.langgraph.nodes.agente_g_node import AgenteGNode
from src.infrastructure.langgraph.state_schema import GraphState, WorkflowStatus, StateMutator


class DummyAgent:
    def __init__(self, *, message: str = "ok", data: dict | None = None, status: TaskStatus = TaskStatus.COMPLETED) -> None:
        self._message = message
        self._data = data or {}
        self._status = status
        self.agent_email = "agente.g@example.com"

    def process(self, task):
        return AgentResult(
            task_id=task.task_id,
            agent_name="agente_g",
            status=self._status,
            message=self._message,
            data=self._data,
        )


@pytest.fixture
def base_state() -> GraphState:
    return GraphState(
        session_id="session-1",
        trace_id="trace-1",
        user_id="user-1",
        original_query="listar correos",
        workflow_mode="chat",
        interaction_channel="chat",
        external_payload={},
        timestamp=datetime.utcnow(),
    )


def test_agente_g_node_with_instruction(monkeypatch, base_state):
    instruction = {
        "operation": "list_gmail",
        "parameters": {"query": "is:unread"},
    }
    state_with_meta = StateMutator.merge_dict(base_state, "response_metadata", {"agente_g_instruction": instruction})

    dummy_agent = DummyAgent(message="Listado de correos", data={"artifact": {"type": "email"}, "metrics": {"google_api_calls": 2}})
    monkeypatch.setattr(AgenteGNode, "_initialize_agent", lambda self: (dummy_agent, None))

    node = AgenteGNode()
    result_state = node.run(state_with_meta)

    assert "agente_g" in result_state.completed_nodes
    assert "Listado de correos" in result_state.response_message
    assert result_state.shared_artifacts.get("agente_g")
    assert result_state.response_metadata.get("agente_g_operation") == "list_gmail"
    assert result_state.response_metadata.get("google_metrics", {}).get("google_api_calls") == 2


def test_agente_g_node_missing_instruction(monkeypatch, base_state):
    dummy_agent = DummyAgent()
    monkeypatch.setattr(AgenteGNode, "_initialize_agent", lambda self: (dummy_agent, None))
    node = AgenteGNode()
    custom_state = base_state.model_copy(update={"original_query": "hola"})
    result_state = node.run(custom_state)
    assert result_state.status == WorkflowStatus.INITIALIZED
    assert "instruccion" in result_state.response_message.lower()
    assert "agente_g_missing_instruction" in [err.get("error_type") for err in result_state.errors]
