import os

os.environ.setdefault("FEATURE_SEMANTIC_NLP", "enabled")

from src.application.nlp.intent_classifier import IntentClassificationResult
from src.core.semantics.intent_service import IntentResult
from src.domain.contracts.intent import Intent
from src.infrastructure.langgraph.nodes.intent_node import IntentNode
from src.infrastructure.langgraph.state_schema import GraphState


class RecordingClassifier:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def classify(self, query: str, use_semantic: bool = True) -> IntentClassificationResult:
        self.calls.append({"query": query, "use_semantic": use_semantic})
        semantic = None
        if use_semantic:
            semantic = IntentResult(
                intent=Intent.SMALL_TALK,
                confidence=0.5,
                target_agent="capi_gus",
                entities={"sample": True},
                context_resolved=True,
                reasoning="semantic reasoning",
                requires_clarification=False,
                provider="openai",
                model="gpt-test",
            )
        return IntentClassificationResult(
            intent=Intent.SMALL_TALK,
            confidence=0.5,
            matched_patterns=["pattern"],
            reasoning="stub",
            semantic_result=semantic,
        )


def _make_state(interaction_channel: str | None) -> GraphState:
    payload = {"interaction_channel": interaction_channel} if interaction_channel else {}
    config = {"interaction_channel": interaction_channel} if interaction_channel else {}
    kwargs: dict[str, object] = {
        "session_id": "sess",
        "trace_id": "trace",
        "user_id": "user",
        "original_query": "hola mundo",
        "workflow_mode": "voice" if interaction_channel == "voice" else "chat",
        "external_payload": payload,
        "config": config,
    }
    if interaction_channel:
        kwargs["interaction_channel"] = interaction_channel
    return GraphState(**kwargs)


def test_intent_node_disables_semantic_for_voice_channel():
    node = IntentNode()
    recorder = RecordingClassifier()
    node.classifier = recorder  # type: ignore[assignment]

    state = _make_state("voice")
    updated = node.run(state)

    assert recorder.calls, "classifier should be invoked"
    assert recorder.calls[0]["use_semantic"] is False
    metadata = updated.response_metadata or {}
    classification = metadata.get("intent_classification") or {}
    assert classification.get("semantic_enabled") is False
    assert classification.get("source") == "legacy"
    assert "semantic_result" not in classification
    assert metadata.get("intent_semantic_enabled") is False


def test_intent_node_keeps_semantic_for_chat_channel():
    node = IntentNode()
    recorder = RecordingClassifier()
    node.classifier = recorder  # type: ignore[assignment]

    state = _make_state(None)
    updated = node.run(state)

    assert recorder.calls, "classifier should be invoked"
    assert recorder.calls[0]["use_semantic"] is True
    metadata = updated.response_metadata or {}
    classification = metadata.get("intent_classification") or {}
    assert classification.get("semantic_enabled") is True
    semantic_payload = classification.get("semantic_result")
    assert isinstance(semantic_payload, dict)
    assert semantic_payload.get("intent") == Intent.SMALL_TALK.value
    assert metadata.get("intent_semantic_enabled") is True
