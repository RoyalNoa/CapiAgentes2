import base64
import json
from datetime import datetime
from pathlib import Path

import pytest

from ia_workspace.agentes.agente_g.push_service import AgenteGPushService, AgenteGPushSettings
from ia_workspace.agentes.agente_g.handler import AgenteGAgent
from src.domain.agents.agent_models import AgentTask, IntentType, TaskStatus


class FakeGmailClient:
    def __init__(self) -> None:
        self.watch_kwargs = None
        self.history_calls = []
        self.history_response = {"history": []}

    def watch_mailbox(self, **kwargs):
        self.watch_kwargs = kwargs
        return {"historyId": "123", "expiration": "999999"}

    def stop_watch(self):
        return {"stopped": True}

    def list_history(self, **kwargs):
        self.history_calls.append(kwargs)
        return self.history_response


@pytest.fixture
def push_env(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_GMAIL_PUSH_TOPIC", "projects/test/topics/agente-g")
    monkeypatch.setenv("GOOGLE_GMAIL_PUSH_VERIFICATION_TOKEN", "secret-token")
    monkeypatch.setenv("GOOGLE_GMAIL_PUSH_LABEL_IDS", "INBOX")
    monkeypatch.setenv("GOOGLE_GMAIL_PUSH_LABEL_ACTION", "include")
    monkeypatch.setenv("AGENTE_G_STORAGE_DIR", str(tmp_path))
    return tmp_path


def test_push_service_enable_updates_status(tmp_path, push_env):
    fake_gmail = FakeGmailClient()
    settings = AgenteGPushSettings.load_from_env()
    service = AgenteGPushService(
        gmail_client=fake_gmail,
        settings=settings,
        clock=lambda: datetime(2025, 1, 1, 12, 0, 0),
    )

    status = service.enable_push()

    assert status["active"] is True
    assert fake_gmail.watch_kwargs["topic_name"] == "projects/test/topics/agente-g"
    assert fake_gmail.watch_kwargs["label_ids"] == ["INBOX"]

    status_path = Path(settings.status_file)
    assert status_path.exists()
    stored = json.loads(status_path.read_text(encoding="utf-8"))
    assert stored["last_history_id"] == "123"


def test_push_service_processes_notification(push_env):
    fake_gmail = FakeGmailClient()
    fake_gmail.history_response = {
        "history": [
            {
                "id": "125",
                "messagesAdded": [
                    {
                        "message": {
                            "id": "msg-1",
                            "threadId": "thr-1",
                            "labelIds": ["INBOX"],
                        }
                    }
                ],
                "labelsRemoved": [
                    {
                        "message": {
                            "id": "msg-2",
                            "threadId": "thr-2",
                        },
                        "labelIds": ["UNREAD"],
                    }
                ],
            }
        ]
    }

    settings = AgenteGPushSettings.load_from_env()
    service = AgenteGPushService(
        gmail_client=fake_gmail,
        settings=settings,
        clock=lambda: datetime(2025, 1, 1, 12, 0, 0),
    )
    service.enable_push()

    payload_data = {"historyId": "125", "emailAddress": "user@example.com"}
    payload = {
        "message": {
            "data": base64.b64encode(json.dumps(payload_data).encode("utf-8")).decode("utf-8"),
            "attributes": {"token": "secret-token"},
        }
    }

    result = service.handle_notification(payload, auth_header="Bearer secret-token")

    assert result["status"] == "processed"
    assert result["update_count"] == 2
    assert any(update["type"] == "message_added" for update in result["updates"])
    assert fake_gmail.history_calls[0]["start_history_id"] == "123"

    status = service.get_status()
    assert status["last_history_id"] == "125"

    snapshot_path = Path(result["snapshot_path"])
    assert snapshot_path.exists()


def test_agente_g_agent_handles_push_operations():
    class StubPushService:
        def __init__(self) -> None:
            self.enabled = False
            self.calls = []

        def enable_push(self, **kwargs):
            self.calls.append(("enable", kwargs))
            self.enabled = True
            return {"active": True, "topic_name": kwargs.get("topic_name")}

        def disable_push(self):
            self.calls.append(("disable", {}))
            self.enabled = False
            return {"active": False}

        def get_status(self):
            self.calls.append(("status", {}))
            return {"active": self.enabled}

    stub_push = StubPushService()

    # Objetos mínimos para evitar carga de credenciales
    agent = AgenteGAgent(
        gmail_client=object(),
        drive_client=object(),
        calendar_client=object(),
        push_service=stub_push,
    )

    task_enable = AgentTask(
        task_id="task-1",
        intent=IntentType.QUERY.value,
        query="habilitar push",
        user_id="user",
        session_id="session",
        metadata={"operation": "enable_gmail_push", "parameters": {"topic_name": "topic"}},
    )
    result_enable = agent.process(task_enable)
    assert result_enable.status == TaskStatus.COMPLETED
    assert result_enable.data["result"]["status"]["active"] is True

    task_status = AgentTask(
        task_id="task-2",
        intent=IntentType.QUERY.value,
        query="estado push",
        user_id="user",
        session_id="session",
        metadata={"operation": "get_gmail_push_status", "parameters": {}},
    )
    result_status = agent.process(task_status)
    assert result_status.status == TaskStatus.COMPLETED
    assert result_status.data["result"]["status"]["active"] is True

    task_disable = AgentTask(
        task_id="task-3",
        intent=IntentType.QUERY.value,
        query="detener push",
        user_id="user",
        session_id="session",
        metadata={"operation": "disable_gmail_push", "parameters": {}},
    )
    result_disable = agent.process(task_disable)
    assert result_disable.status == TaskStatus.COMPLETED
    assert result_disable.data["result"]["status"]["active"] is False

