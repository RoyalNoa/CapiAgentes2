import sys
import unicodedata
from base64 import urlsafe_b64encode
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
IA_WORKSPACE = BACKEND_DIR / "ia_workspace"
if IA_WORKSPACE.exists() and str(IA_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(IA_WORKSPACE))

from agentes.agente_g.handler import AgenteGAgent
from src.domain.agents.agent_models import AgentResult, IntentType, TaskStatus
from src.domain.agents.agent_protocol import AgentTask
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


class StubGmailClient:
    def __init__(self) -> None:
        self._messages = {
            "1": self._build_message(
                message_id="1",
                subject="Pedido de fondos Sucursal Córdoba",
                body="Sucursal Córdoba\nNecesita USD 5,000 para cubrir caja chica.",
                unread=True,
                date="Thu, 10 Oct 2025 12:00:00 +0000",
            ),
            "2": self._build_message(
                message_id="2",
                subject="Reposición sucursal Rosario",
                body="Sucursal Rosario: $3.200 para reponer efectivo de ventanilla.",
                unread=False,
                date="Thu, 10 Oct 2025 13:00:00 +0000",
            ),
            "sent-1": self._build_message(
                message_id="sent-1",
                subject="Confirmación enviada",
                body="Envié la confirmación por $1.000.",
                unread=False,
                from_addr="Capi Agente <capiagente@gmail.com>",
                label_ids=["SENT"],
                date="Thu, 10 Oct 2025 14:00:00 +0000",
            ),
        }

    @staticmethod
    def _build_message(
        *,
        message_id: str,
        subject: str,
        body: str,
        unread: bool,
        from_addr: str = "tesoreria@example.com",
        label_ids: Optional[List[str]] = None,
        date: str = "Thu, 10 Oct 2025 12:00:00 +0000",
    ) -> dict:
        encoded_body = urlsafe_b64encode(body.encode("utf-8")).decode("utf-8").rstrip("=")
        final_label_ids = list(label_ids) if label_ids is not None else ["INBOX"]
        if label_ids is None and unread:
            final_label_ids.append("UNREAD")
        return {
            "id": message_id,
            "threadId": f"thread-{message_id}",
            "labelIds": final_label_ids,
            "snippet": body[:100],
            "payload": {
                "mimeType": "text/plain",
                "headers": [
                    {"name": "From", "value": from_addr},
                    {"name": "Subject", "value": subject},
                    {"name": "Date", "value": date},
                ],
                "body": {"data": encoded_body},
            },
        }

    def list_messages(self, *, query=None, label_ids=None, max_results=None):
        return {"messages": [{"id": key} for key in self._messages.keys()]}

    def get_message(self, message_id: str, format: str = "full") -> dict:
        return self._messages[message_id]

    # No-op placeholders to satisfy interface when other operations are invoked.
    def send_plain_text(self, **kwargs):
        raise NotImplementedError


class StubDriveClient:
    pass


class StubCalendarClient:
    pass


class StubPushService:
    def enable_push(self, **kwargs):
        return {"active": True, "topic_name": kwargs.get("topic_name")}

    def disable_push(self):
        return {"active": False, "updated_at": "2025-10-10T00:00:00Z"}

    def get_status(self):
        return {"active": False, "last_history_id": None, "last_error": None}


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


def test_agente_g_node_infers_list_unread_for_new_mails(monkeypatch, base_state):
    dummy_agent = DummyAgent()
    monkeypatch.setattr(AgenteGNode, "_initialize_agent", lambda self: (dummy_agent, None))
    node = AgenteGNode()
    query = "Quiero saber si llegaron nuevos mails y cuánto dinero necesitan las sucursales"
    query_state = base_state.model_copy(update={"original_query": query})

    result_state = node.run(query_state)

    assert result_state.response_message
    assert dummy_agent.last_task is not None
    assert dummy_agent.last_task.metadata["operation"] == "list_gmail"
    params = dummy_agent.last_task.metadata["parameters"]
    assert params.get("query") == "is:unread"


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


def test_agente_g_agent_list_gmail_aggregates_branch_totals():
    agent = AgenteGAgent(
        gmail_client=StubGmailClient(),
        drive_client=StubDriveClient(),
        calendar_client=StubCalendarClient(),
        push_service=StubPushService(),
        compose_with_llm=False,
    )

    task = AgentTask(
        task_id="task-1",
        intent=IntentType.QUERY,
        query="Quiero saber si llegaron nuevos mails y cuánto dinero necesitan las sucursales",
        user_id="user-1",
        session_id="session-1",
        context={},
        metadata={"operation": "list_gmail", "parameters": {"query": "is:unread"}},
    )

    result = agent.process(task)

    assert result.status is TaskStatus.COMPLETED
    payload = result.data or {}
    operation_result = payload.get("result") or {}
    branch_totals = operation_result.get("branch_totals") or {}
    messages = operation_result.get("messages") or []

    def normalize(label: str) -> str:
        decomposed = unicodedata.normalize("NFD", label or "")
        stripped = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
        return stripped.lower()

    normalized_totals = {normalize(key): value for key, value in branch_totals.items()}

    cordoba_total = normalized_totals.get("sucursal cordoba", 0.0)
    rosario_total = normalized_totals.get("sucursal rosario", 0.0)

    assert cordoba_total == pytest.approx(5000.0)
    assert rosario_total == pytest.approx(3200.0)
    assert all("capiagente@gmail.com" not in (msg.get("from") or "").lower() for msg in messages)

    artifact = payload.get("artifact") or {}
    assert artifact.get("branch_totals") == branch_totals
    assert "Detalle por sucursal" in (result.message or "")
    assert "Monto total detectado: 8.200,00" in (result.message or "")
    assert "(no leídos: 1)" in (result.message or "")


def test_agente_g_list_gmail_only_unread_filter():
    agent = AgenteGAgent(
        gmail_client=StubGmailClient(),
        drive_client=StubDriveClient(),
        calendar_client=StubCalendarClient(),
        push_service=StubPushService(),
        compose_with_llm=False,
    )

    task = AgentTask(
        task_id="task-2",
        intent=IntentType.QUERY,
        query="Mostrame los correos sin leer",
        user_id="user-1",
        session_id="session-2",
        context={},
        metadata={"operation": "list_gmail", "parameters": {"only_unread": True}},
    )

    result = agent.process(task)

    assert result.status is TaskStatus.COMPLETED
    payload = result.data or {}
    operation_result = payload.get("result") or {}
    messages = operation_result.get("messages") or []
    assert len(messages) == 1
    assert messages[0].get("unread") is True
    assert operation_result.get("total_amount") == pytest.approx(5000.0)
    assert "correos sin leer" in (result.message or "")
