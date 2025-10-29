"""
Intent detection node: classifies the user's query and updates state.detected_intent
with confidence and reasoning metadata, logging details for observability.
"""
from __future__ import annotations

from typing import Any, Dict

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.application.nlp.intent_classifier import IntentClassifier
from src.core.feature_flags import is_semantic_nlp_enabled
from src.core.logging import get_logger
from src.domain.contracts.intent import Intent

logger = get_logger(__name__)


class IntentNode(GraphNode):
    def __init__(self, name: str = "intent") -> None:
        super().__init__(name=name)
        self.classifier = IntentClassifier()

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "intent_node_start", "node": self.name})
        text = state.original_query or ""
        channel_candidate = getattr(state, "interaction_channel", None)
        if not channel_candidate and isinstance(getattr(state, "config", None), dict):
            channel_candidate = state.config.get("interaction_channel")
        if not channel_candidate and isinstance(getattr(state, "external_payload", None), dict):
            payload_channel = state.external_payload.get("interaction_channel") or state.external_payload.get("channel")
            channel_candidate = payload_channel or channel_candidate
        if not channel_candidate:
            channel_candidate = state.workflow_mode if getattr(state, "workflow_mode", None) else None
        channel_normalized = (channel_candidate or "").strip().lower()

        session_identifier = getattr(state, "session_id", None) or "global"
        semantic_flag_enabled = True
        try:
            semantic_flag_enabled = is_semantic_nlp_enabled(session_identifier)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning(
                {
                    "event": "intent_node_feature_flag_check_failed",
                    "session_id": session_identifier,
                    "error": str(exc),
                }
            )
            semantic_flag_enabled = True

        use_semantic = channel_normalized != "voice" and semantic_flag_enabled
        if not use_semantic:
            reason = "voice_channel_detected" if channel_normalized == "voice" else "feature_flag_disabled"
            logger.info(
                {
                    "event": "intent_node_semantic_bypassed",
                    "reason": reason,
                    "channel": channel_normalized or None,
                    "session_id": session_identifier,
                }
            )
        result = self.classifier.classify(text, use_semantic=use_semantic)
        semantic_available = use_semantic and result.semantic_result is not None

        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.update_field(s, "detected_intent", result.intent)
        s = StateMutator.update_field(s, "intent_confidence", result.confidence)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)
        classification_record: Dict[str, Any] = {
            "intent": getattr(result.intent, "value", str(result.intent)),
            "confidence": result.confidence,
            "matched_patterns": list(result.matched_patterns or []),
            "reasoning": result.reasoning,
            "semantic_enabled": semantic_available,
            "source": "semantic" if semantic_available else "legacy",
        }
        if result.semantic_result is not None:
            classification_record["semantic_result"] = _serialize_semantic_result(result.semantic_result)

        s = StateMutator.merge_dict(
            s,
            "response_metadata",
            {
                "intent_reasoning": result.reasoning,
                "intent_matched_patterns": result.matched_patterns,
                "intent_semantic_enabled": semantic_available,
                "interaction_channel": channel_normalized or None,
                "intent_classification": classification_record,
            },
        )

        # Remove early response - let the pipeline handle responses properly
        # Early responses cause issues with complex queries

        logger.info(
            {
                "event": "intent_node_end",
                "intent": getattr(result.intent, "value", str(result.intent)),
                "confidence": round(result.confidence, 3),
            }
        )
        return s
def _serialize_semantic_result(result: Any) -> Dict[str, Any]:
    """Transform an IntentResult into a JSON-serializable dict."""
    if result is None:
        return {}

    intent_value = getattr(result, "intent", None)
    confidence = getattr(result, "confidence", 0.0)
    target_agent = getattr(result, "target_agent", "")
    entities = getattr(result, "entities", {}) or {}
    context_resolved = getattr(result, "context_resolved", False)
    reasoning = getattr(result, "reasoning", "")
    requires_clarification = getattr(result, "requires_clarification", False)
    provider = getattr(result, "provider", "")
    model = getattr(result, "model", "")

    serialized = {
        "intent": intent_value.value if isinstance(intent_value, Intent) else intent_value,
        "confidence": confidence,
        "target_agent": target_agent,
        "entities": entities,
        "context_resolved": context_resolved,
        "reasoning": reasoning,
        "requires_clarification": requires_clarification,
        "provider": provider,
        "model": model,
    }
    return serialized
