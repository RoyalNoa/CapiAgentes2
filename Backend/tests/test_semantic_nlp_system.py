import json
from typing import Any, Dict

import pytest

from src.core.semantics.intent_service import IntentResult, SemanticIntentService
from src.domain.contracts.intent import Intent
from src.application.reasoning.llm_reasoner import LLMReasoningResult


class StubReasoner:
    def __init__(self, responses: Dict[str, Dict[str, Any]]):
        self.responses = responses

    async def reason(self, query: str, **_: Any) -> LLMReasoningResult:  # pragma: no cover - simple stub
        payload = json.loads(query)
        user_query = payload.get("query", "")
        data = self.responses.get(user_query)
        if data is None:
            return LLMReasoningResult(success=False, response=None, error="no_stub")
        return LLMReasoningResult(success=True, response=json.dumps(data), model="stub-model", confidence_score=data.get("confidence", 0.8))


@pytest.fixture
def intent_service() -> SemanticIntentService:
    responses = {
        "cuanto dinero hay en la sucursal villa crespo": {
            "intent": "db_operation",
            "target_agent": "capi_datab",
            "confidence": 0.92,
            "requires_clarification": False,
            "entities": {"branch": {"name": "Villa Crespo"}},
            "reasoning": "Saldo de sucursal identificado",
        },
        "hola como estas": {
            "intent": "small_talk",
            "target_agent": "capi_gus",
            "confidence": 0.7,
            "requires_clarification": False,
            "entities": {},
            "reasoning": "Saludo detectado",
        },
    }
    return SemanticIntentService(reasoner=StubReasoner(responses))


def test_branch_query_routes_to_datab(intent_service: SemanticIntentService):
    context = {"session_id": "test_session"}
    result = intent_service.classify_intent("cuanto dinero hay en la sucursal villa crespo", context)

    assert isinstance(result, IntentResult)
    assert result.intent == Intent.DB_OPERATION
    assert result.target_agent == "capi_datab"
    assert result.entities["branch"]["name"] == "Villa Crespo"
    assert not result.requires_clarification


def test_capi_gus_detection(intent_service: SemanticIntentService):
    result = intent_service.classify_intent("hola como estas")
    assert result.intent == Intent.SMALL_TALK
    assert result.target_agent == "capi_gus"


def test_fallback_routes_to_agente_g():
    service = SemanticIntentService(reasoner=StubReasoner({}))
    result = service.classify_intent("enviar un correo a ventas@example.com avisando sobre el reporte semanal")
    assert result.target_agent == "agente_g"
    assert result.intent in {Intent.GOOGLE_GMAIL, Intent.GOOGLE_WORKSPACE}
    assert "email_recipients" in result.entities
    assert "ventas@example.com" in result.entities.get("email_recipients", [])


def test_fallback_when_llm_fails():
    service = SemanticIntentService(reasoner=StubReasoner({}))
    result = service.classify_intent("consulta sin soporte")
    assert result.intent in {
        Intent.UNKNOWN,
        Intent.DB_OPERATION,
        Intent.SUMMARY_REQUEST,
        Intent.ANOMALY_QUERY,
        Intent.GOOGLE_WORKSPACE,
    }
    assert result.target_agent in {"assemble", "capi_datab", "capi_gus", "summary", "anomaly", "agente_g"}


def test_requires_clarification_propagated(intent_service: SemanticIntentService):
    intent_service.reasoner.responses["consulta vaga"] = {
        "intent": "unknown",
        "target_agent": "assemble",
        "confidence": 0.3,
        "requires_clarification": True,
        "entities": {},
        "reasoning": "Faltan datos",
    }
    result = intent_service.classify_intent("consulta vaga")
    assert result.requires_clarification is True
