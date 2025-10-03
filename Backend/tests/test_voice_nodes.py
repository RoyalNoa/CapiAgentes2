import pytest

from src.infrastructure.langgraph.nodes.voice_transcription_node import VoiceTranscriptionNode
from src.infrastructure.langgraph.nodes.voice_synthesis_node import VoiceSynthesisNode
from src.infrastructure.langgraph.state_schema import GraphState


def _make_state(**overrides):
    base = {
        "session_id": "sess-1",
        "trace_id": "trace-1",
        "user_id": "user-1",
        "original_query": "hola voz",
    }
    base.update(overrides)
    return GraphState(**base)


def test_voice_transcription_populates_metadata_for_voice_channel():
    state = _make_state(
        interaction_channel="voice",
        external_payload={"language": "es-ES", "sample_rate": 16000, "session_id": "voice-42"},
    )
    node = VoiceTranscriptionNode()

    updated = node.run(state)

    assert updated.current_node == "voice_transcription"
    assert updated.completed_nodes[-1] == "voice_transcription"
    assert updated.response_metadata["voice"]["transcript"] == "hola voz"
    assert updated.response_metadata["voice"]["sample_rate_hz"] == 16000
    assert updated.response_metadata["voice_transcription"]["transcript_present"] is True
    assert updated.shared_artifacts["voice"]["transcript"] == "hola voz"


def test_voice_transcription_noop_for_non_voice_channel():
    state = _make_state(interaction_channel="chat")
    node = VoiceTranscriptionNode()

    updated = node.run(state)

    assert updated.current_node == "voice_transcription"
    assert updated.completed_nodes[-1] == "voice_transcription"
    assert updated.response_metadata == {}
    assert updated.shared_artifacts == {}


def test_voice_synthesis_merges_existing_voice_metadata():
    state = _make_state(
        interaction_channel="voice",
        response_message="respuesta sintetica",
        response_metadata={"voice": {"transcript": "hola voz"}},
        shared_artifacts={"voice": {"transcript": "hola voz"}},
    )
    node = VoiceSynthesisNode()

    updated = node.run(state)

    voice_meta = updated.response_metadata["voice"]
    assert voice_meta["transcript"] == "hola voz"
    assert voice_meta["synthesis_requested"] is True
    assert "response_preview" in voice_meta
    assert updated.shared_artifacts["voice"]["response_text"] == "respuesta sintetica"


def test_voice_synthesis_noop_for_non_voice_channel():
    state = _make_state(interaction_channel="chat", response_message="hola")
    node = VoiceSynthesisNode()

    updated = node.run(state)

    assert updated.current_node == "voice_synthesis"
    assert updated.completed_nodes[-1] == "voice_synthesis"
    assert updated.response_metadata == {}
    assert updated.shared_artifacts == {}

