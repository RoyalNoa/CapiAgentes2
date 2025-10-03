import os
import json
import pytest

from src.core.feature_flags import FeatureFlagStatus, get_feature_flag_manager
from src.core.monitoring import get_semantic_metrics
from src.core.semantics.intent_service import SemanticIntentService
from src.infrastructure.langgraph.nodes.router_node import RouterNode
from src.infrastructure.langgraph.state_schema import GraphState
from src.application.reasoning.llm_reasoner import LLMReasoningResult


class RouterStubReasoner:
    def __init__(self):
        self._responses = {}

    def add_response(self, query: str, payload: dict) -> None:
        self._responses[query] = payload

    async def reason(self, query: str, **_: object) -> LLMReasoningResult:  # pragma: no cover - stub
        payload = json.loads(query)
        user_query = payload.get("query", "")
        data = self._responses.get(user_query)
        if data is None:
            return LLMReasoningResult(success=False, response=None, error="missing_stub")
        return LLMReasoningResult(success=True, response=json.dumps(data), model="stub-router", confidence_score=data.get("confidence", 0.8))


@pytest.fixture(autouse=True)
def configure_environment(monkeypatch):
    os.environ.setdefault("SECRET_KEY", "test_secret_key")
    os.environ.setdefault("API_KEY_BACKEND", "test")
    os.environ.setdefault("LOG_LEVEL", "INFO")
    os.environ.setdefault("ENVIRONMENT", "development")
    os.environ.setdefault("DATABASE_URL", "sqlite:///test_router.db")
    os.environ.setdefault("OPENAI_API_KEY", "")

    # Reset feature flags and metrics
    flag_manager = get_feature_flag_manager()
    flag_manager.update_flag("semantic_nlp", FeatureFlagStatus.ENABLED, 100)
    metrics = get_semantic_metrics()
    metrics._intent_metrics.clear()
    metrics._metrics_buffer.clear()
    metrics._counters.clear()
    metrics._errors.clear()


@pytest.fixture
def router_with_stub(monkeypatch):
    reasoner = RouterStubReasoner()
    reasoner.add_response(
        "encontrar outliers en datos financieros",
        {
            "intent": "anomaly_query",
            "target_agent": "anomaly",
            "confidence": 0.9,
            "requires_clarification": False,
            "entities": {},
            "reasoning": "Consulta orientada a detección de anomalías",
        },
    )

    def factory(*args, **kwargs):
        return SemanticIntentService(reasoner=reasoner)

    monkeypatch.setattr("src.infrastructure.langgraph.nodes.router_node.SemanticIntentService", factory)
    return RouterNode()


def test_router_uses_semantic_result(router_with_stub):
    state = GraphState(
        user_query="encontrar outliers en datos financieros",
        original_query="encontrar outliers en datos financieros",
        session_id="router_semantic",
        trace_id="trace_A",
        user_id="user_A",
    )

    updated = router_with_stub.run(state)
    assert updated.routing_decision == "anomaly"
    semantic_meta = updated.response_metadata.get("semantic_result")
    assert semantic_meta["intent"] == "anomaly_query"
    assert semantic_meta["provider"] == "openai" or semantic_meta["provider"] == "fallback"


def test_feature_flag_disables_semantic(router_with_stub):
    flag_manager = get_feature_flag_manager()
    flag_manager.update_flag("semantic_nlp", FeatureFlagStatus.DISABLED, 0)

    state = GraphState(
        user_query="consulta sin soporte",
        original_query="consulta sin soporte",
        session_id="router_legacy",
        trace_id="trace_B",
        user_id="user_B",
    )

    updated = router_with_stub.run(state)
    assert updated.routing_decision in {"assemble", "capi_datab", "summary", "anomaly"}


def test_metrics_are_tracked(router_with_stub):
    metrics = get_semantic_metrics()
    state = GraphState(
        user_query="encontrar outliers en datos financieros",
        original_query="encontrar outliers en datos financieros",
        session_id="router_metrics",
        trace_id="trace_C",
        user_id="user_C",
    )

    router_with_stub.run(state)
    health = metrics.get_system_health()
    assert health.requests_per_minute >= 1


def test_emergency_disable():
    flag_manager = get_feature_flag_manager()
    assert flag_manager.is_enabled("semantic_nlp", "session") is True
    flag_manager.emergency_disable("semantic_nlp", "test")
    assert flag_manager.is_enabled("semantic_nlp", "session") is False

