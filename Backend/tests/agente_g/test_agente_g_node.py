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
        self.last_task = None

    def process(self, task):
        self.last_task = task
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
    assert result_state.response_metadata.get("requires_human_approval") is False


def test_agente_g_node_missing_instruction(monkeypatch, base_state):
    dummy_agent = DummyAgent()
    monkeypatch.setattr(AgenteGNode, "_initialize_agent", lambda self: (dummy_agent, None))
    node = AgenteGNode()
    custom_state = base_state.model_copy(update={"original_query": "hola"})
    result_state = node.run(custom_state)
    assert result_state.status == WorkflowStatus.INITIALIZED
    assert "instruccion" in result_state.response_message.lower()
    assert "agente_g_missing_instruction" in [err.get("error_type") for err in result_state.errors]


def test_agente_g_node_infers_send_email_from_query(monkeypatch, base_state):
    dummy_agent = DummyAgent()
    monkeypatch.setattr(AgenteGNode, "_initialize_agent", lambda self: (dummy_agent, None))
    node = AgenteGNode()
    query_state = base_state.model_copy(update={"original_query": "Envia un correo a finanzas@example.com con asunto Reporte semanal"})

    result_state = node.run(query_state)

    assert result_state.response_message
    assert dummy_agent.last_task is not None
    assert dummy_agent.last_task.metadata["operation"] == "send_gmail"
    params = dummy_agent.last_task.metadata["parameters"]
    assert params.get("compose_context")
    assert params.get("to") == ["finanzas@example.com"]
    assert "Capi Gus te confirma" in (result_state.response_message or "")
    metadata = result_state.response_metadata or {}
    assert metadata.get("requires_human_approval") is False
    assert metadata.get("active_agent") == "capi_gus"
    assert metadata.get("workflow_stage") == "capi_gus_followup"


def test_agente_g_node_rejects_invalid_email_recipient(monkeypatch, base_state):
    dummy_agent = DummyAgent()
    monkeypatch.setattr(AgenteGNode, "_initialize_agent", lambda self: (dummy_agent, None))
    node = AgenteGNode()
    invalid_query = "Envia un correo a lucasnoa94gmail.com que diga hola mundo"
    state = base_state.model_copy(update={"original_query": invalid_query})

    result_state = node.run(state)

    assert dummy_agent.last_task is None
    assert "correo" in (result_state.response_message or "").lower()
    metadata = result_state.response_metadata or {}
    assert metadata.get("validation_error") == "invalid_email_recipients"
    assert metadata.get("requires_clarification") is True
