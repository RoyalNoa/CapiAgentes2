"""
Intent detection node: classifies the user's query and updates state.detected_intent
with confidence and reasoning metadata, logging details for observability.
"""
from __future__ import annotations

from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator
from src.application.nlp.intent_classifier import IntentClassifier
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
        result = self.classifier.classify(text)

        s = StateMutator.update_field(state, "current_node", self.name)
        s = StateMutator.update_field(s, "detected_intent", result.intent)
        s = StateMutator.update_field(s, "intent_confidence", result.confidence)
        s = StateMutator.append_to_list(s, "completed_nodes", self.name)
        s = StateMutator.merge_dict(
            s,
            "response_metadata",
            {
                "intent_reasoning": result.reasoning,
                "intent_matched_patterns": result.matched_patterns,
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
