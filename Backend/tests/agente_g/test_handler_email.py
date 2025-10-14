import json
from typing import Any, Dict, List

from ia_workspace.agentes.agente_g.handler import AgenteGAgent
from src.application.reasoning.llm_reasoner import LLMReasoningResult
from src.domain.agents.agent_models import AgentTask, IntentType, TaskStatus


class StubReasoner:
    def __init__(self, response: Dict[str, Any]):
        self._response = json.dumps(response)

    async def reason(self, **_: Any) -> LLMReasoningResult:
        return LLMReasoningResult(
            success=True,
            response=self._response,
            prompt_tokens=10,
            completion_tokens=20,
            total_tokens=30,
            model="stub-model",
        )


class StubGmailClient:
    def __init__(self) -> None:
        self.payload: Dict[str, Any] | None = None

    def send_plain_text(self, *, to: List[str], subject: str, body: str, cc=None, bcc=None, sender=None) -> Dict[str, Any]:
        self.payload = {
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "bcc": bcc,
            "sender": sender,
        }
        return {"id": "msg-1", "threadId": "thr-1"}


class StubPushService:
    pass


def _build_task(metadata: Dict[str, Any]) -> AgentTask:
    return AgentTask(
        task_id="task-1",
        intent=IntentType.QUERY.value,
        query="Envia un correo cordial agradeciendo el reporte",
        user_id="user",
        session_id="session",
        metadata=metadata,
    )


def test_agent_uses_llm_to_compose_email():
    gmail = StubGmailClient()
    agent = AgenteGAgent(
        gmail_client=gmail,
        drive_client=object(),
        calendar_client=object(),
        push_service=StubPushService(),
        llm_reasoner=StubReasoner({"subject": "Gracias por el reporte", "body": "Equipo,\nGracias por enviar el reporte.\nSaludos.\n"}),
        compose_with_llm=True,
    )

    metadata = {
        "operation": "send_gmail",
        "parameters": {
            "to": ["reportes@example.com"],
            "compose_context": "Agradece el reporte trimestral y solicita confirmación de recibo.",
        },
    }
    result = agent.process(_build_task(metadata))

    assert result.status == TaskStatus.COMPLETED
    assert gmail.payload is not None
    assert gmail.payload["subject"] == "Gracias por el reporte"
    assert "Agradece el reporte" not in gmail.payload["body"]  # body viene del LLM
