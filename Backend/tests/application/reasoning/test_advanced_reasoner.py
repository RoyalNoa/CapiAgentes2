from types import SimpleNamespace

import pytest

from src.application.reasoning.advanced_reasoner import AdvancedReasoner
from src.core.semantics.intent_service import IntentResult
from src.domain.contracts.intent import Intent
from src.infrastructure.langgraph.state_schema import GraphState


class DummySemanticService:
    def __init__(self) -> None:
        self.calls = 0

    def classify_intent(self, query: str, context: dict[str, object] | None = None) -> IntentResult:
        self.calls += 1
        return IntentResult(
            intent=Intent.SMALL_TALK,
            confidence=0.42,
            target_agent="capi_gus",
            entities={},
            reasoning="semantic fallback",
        )


class DummyConfigService:
    def list_status(self):
        return [
            SimpleNamespace(name="summary", enabled=True),
            SimpleNamespace(name="capi_gus", enabled=True),
            SimpleNamespace(name="capi_desktop", enabled=True),
            SimpleNamespace(name="capi_datab", enabled=True),
            SimpleNamespace(name="anomaly", enabled=True),
            SimpleNamespace(name="branch", enabled=True),
            SimpleNamespace(name="agente_g", enabled=True),
        ]


def _make_state(classification: dict[str, object] | None) -> GraphState:
    metadata = {}
    if classification is not None:
        metadata["intent_classification"] = classification
    return GraphState(
        session_id="sess",
        trace_id="trace",
        user_id="user",
        original_query="hola mundo",
        workflow_mode="chat",
        external_payload={},
        response_metadata=metadata,
    )


def test_generate_plan_reuses_semantic_cache():
    classification = {
        "intent": Intent.GOOGLE_GMAIL.value,
        "confidence": 0.91,
        "matched_patterns": ["semantic_pattern:google_gmail"],
        "reasoning": "semantic reasoning",
        "semantic_enabled": True,
        "source": "semantic",
        "semantic_result": {
            "intent": Intent.GOOGLE_GMAIL.value,
            "confidence": 0.91,
            "target_agent": "agente_g",
            "entities": {"gmail_operation": "read"},
            "context_resolved": True,
            "reasoning": "router-success",
            "requires_clarification": False,
            "provider": "openai",
            "model": "gpt-4o-mini",
        },
    }
    state = _make_state(classification)
    semantic = DummySemanticService()
    reasoner = AdvancedReasoner(semantic_service=semantic, config_service=DummyConfigService())

    plan = reasoner.generate_plan(
        query="abrime el correo",
        session_id="sess",
        user_id="user",
        state=state,
    )

    assert semantic.calls == 0
    assert plan.supporting_evidence.get("semantic_cached") is True
    assert plan.supporting_evidence.get("intent_source") == "semantic"
    assert plan.intent == Intent.GOOGLE_GMAIL.value


def test_generate_plan_calls_semantic_when_cache_missing():
    state = _make_state(None)
    semantic = DummySemanticService()
    reasoner = AdvancedReasoner(semantic_service=semantic, config_service=DummyConfigService())

    plan = reasoner.generate_plan(
        query="hola",
        session_id="sess",
        user_id="user",
        state=state,
    )

    assert semantic.calls == 1
    assert plan.supporting_evidence.get("semantic_cached") is False
    assert plan.intent == Intent.SMALL_TALK.value


def test_generate_plan_reuses_legacy_classification_when_semantic_disabled():
    classification = {
        "intent": Intent.SMALL_TALK.value,
        "confidence": 0.4,
        "matched_patterns": ["legacy"],
        "reasoning": "legacy reasoning",
        "semantic_enabled": False,
        "source": "legacy",
    }
    state = _make_state(classification)
    semantic = DummySemanticService()
    reasoner = AdvancedReasoner(semantic_service=semantic, config_service=DummyConfigService())

    plan = reasoner.generate_plan(
        query="hola",
        session_id="sess",
        user_id="user",
        state=state,
    )

    assert semantic.calls == 0
    assert plan.supporting_evidence.get("semantic_cached") is True
    assert plan.supporting_evidence.get("intent_source") == "legacy"
    assert plan.intent == Intent.SMALL_TALK.value
