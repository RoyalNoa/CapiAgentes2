"""
Voice transcription pre-processing node for LangGraph workflows.
Registers transcript metadata when the interaction channel is voice.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

from src.core.logging import get_logger
from src.infrastructure.langgraph.nodes.base import GraphNode
from src.infrastructure.langgraph.state_schema import GraphState, StateMutator

logger = get_logger(__name__)


class VoiceTranscriptionNode(GraphNode):
    """Annotate graph state with voice transcription metadata."""

    def __init__(self, name: str = "voice_transcription") -> None:
        super().__init__(name=name)

    def run(self, state: GraphState) -> GraphState:
        logger.info({"event": "voice_transcription_node_start", "channel": getattr(state, "interaction_channel", None)})

        updated = StateMutator.update_field(state, "current_node", self.name)
        updated = StateMutator.append_to_list(updated, "completed_nodes", self.name)

        if (state.interaction_channel or "chat").lower() != "voice":
            return updated

        transcript = (state.original_query or "").strip()
        timestamp = datetime.utcnow().isoformat()
        payload: Dict[str, Any] = state.external_payload if isinstance(state.external_payload, dict) else {}

        language = payload.get("language") or payload.get("locale")
        sample_rate = payload.get("sample_rate") or payload.get("sample_rate_hz")

        metadata = dict(state.response_metadata or {})
        voice_meta = dict(metadata.get("voice", {}))
        voice_meta.update(
            {
                "channel": "voice",
                "transcript": transcript,
                "transcript_length": len(transcript),
                "transcribed_at": timestamp,
            }
        )
        if language:
            voice_meta.setdefault("language", str(language))
        if sample_rate:
            try:
                voice_meta.setdefault("sample_rate_hz", int(sample_rate))
            except (TypeError, ValueError):
                pass
        if payload.get("session_id"):
            voice_meta.setdefault("input_session_id", str(payload["session_id"]))

        metadata["voice"] = voice_meta
        metadata["voice_transcription"] = {
            "timestamp": timestamp,
            "transcript_present": bool(transcript),
        }
        updated = StateMutator.update_field(updated, "response_metadata", metadata)

        artifacts = dict((state.shared_artifacts or {}).get("voice", {}))
        if transcript:
            artifacts["transcript"] = transcript
        if payload:
            artifacts.setdefault("input_payload", payload)
        updated = StateMutator.merge_dict(updated, "shared_artifacts", {"voice": artifacts})

        logger.info(
            {
                "event": "voice_transcription_node_end",
                "transcript_length": len(transcript),
                "language": voice_meta.get("language"),
            }
        )
        return updated
