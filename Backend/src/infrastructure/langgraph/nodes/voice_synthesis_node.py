"""
Voice synthesis metadata node for LangGraph workflows.
Marks that synthesized audio should be generated for voice interactions.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from src.core.logging import get_logger
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator

logger = get_logger(__name__)


class VoiceSynthesisNode(GraphNode):
    """Annotate graph state indicating that voice synthesis is required."""

    def __init__(self, name: str = "voice_synthesis") -> None:
        super().__init__(name=name)

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "voice_synthesis_node_start", "channel": getattr(state, "interaction_channel", None)})

        updated = StateMutator.update_field(state, "current_node", self.name)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        if (state.interaction_channel or "chat").lower() != "voice":
            return updated

        response_text = (state.response_message or "").strip()
        timestamp = datetime.utcnow().isoformat()
        payload: Dict[str, Any] = state.external_payload if isinstance(state.external_payload, dict) else {}

        metadata = dict(state.response_metadata or {})
        voice_meta = dict(metadata.get("voice", {}))
        voice_meta.setdefault("channel", "voice")
        voice_meta.update(
            {
                "synthesis_requested": True,
                "synthesis_requested_at": timestamp,
            }
        )
        if response_text:
            voice_meta["response_preview"] = response_text[:240]
        preferences = payload.get("audio_preferences")
        if isinstance(preferences, dict):
            voice_meta.setdefault("synthesis_preferences", preferences)

        metadata["voice"] = voice_meta
        metadata["voice_synthesis"] = {
            "timestamp": timestamp,
            "status": "pending",
            "response_available": bool(response_text),
        }
        updated = StateMutator.update_field(updated, "response_metadata", metadata)

        artifacts = dict((state.shared_artifacts or {}).get("voice", {}))
        if response_text:
            artifacts["response_text"] = response_text
        updated = StateMutator.merge_dict(updated, "shared_artifacts", {"voice": artifacts})

        logger.info(
            {
                "event": "voice_synthesis_node_end",
                "response_present": bool(response_text),
            }
        )
        return updated
