import base64
from typing import Any, List

import pytest
from fastapi import FastAPI, Request, WebSocket
from fastapi.testclient import TestClient

from src.voice.audio_models import TranscriptSegment, VoiceTurnResult
from src.voice.settings import VoiceSettings
from src.api.voice_endpoints import voice_stream, voice_config


class DummyMetrics:
    def __init__(self) -> None:
        self.finished: List[tuple[str, str | None]] = []
        self.frames: int = 0

    def stream_started(self, *, session_id: str, user_id: str, sample_rate_hz: int, limit_seconds: int) -> Any:
        return object()

    def stream_frame_received(self, ctx: Any, *, bytes_length: int) -> float:
        self.frames += bytes_length
        return 0.0

    def stream_finished(self, ctx: Any, *, result: str, warning_reason: str | None) -> None:
        self.finished.append((result, warning_reason))


class StubVoiceOrchestrator:
    def __init__(self, *, max_seconds: int) -> None:
        self.settings = VoiceSettings()
        self.settings.voice_stream_max_seconds = max_seconds
        self.metrics = DummyMetrics()
        self._complete_calls: List[dict[str, str]] = []

    async def stream_transcripts(self, audio_chunks, *, language_code: str, sample_rate_hz: int):
        seen_data = False
        async for chunk in audio_chunks:
            if chunk is None:
                break
            seen_data = True
            yield TranscriptSegment(text="parcial", is_final=False, stability=0.8, confidence=0.5)
        if seen_data:
            yield TranscriptSegment(text="transcripcion final", is_final=True, stability=1.0, confidence=0.9)

    async def complete_turn(self, *, transcript: str, session_id: str, user_id: str, trace_id: str | None):
        self._complete_calls.append({
            "transcript": transcript,
            "session_id": session_id,
            "user_id": user_id,
        })
        audio_b64 = base64.b64encode(b"voz").decode("ascii")
        return VoiceTurnResult(
            transcript=transcript,
            response_text="respuesta sintetica",
            response_audio_base64=audio_b64,
            response_audio_mime="audio/mpeg",
            audio_url=None,
            metadata={"canal": "voice"},
        )


@pytest.fixture
def voice_app():
    app = FastAPI()

    @app.websocket("/api/voice/stream")
    async def _stream(websocket: WebSocket):
        await voice_stream(websocket)

    @app.get("/api/voice/config")
    async def _config():
        class _DummyRequest:
            def __init__(self, app):
                self.app = app
        return await voice_config(_DummyRequest(app))

    return app


def test_voice_stream_happy_path(voice_app):
    orchestrator = StubVoiceOrchestrator(max_seconds=120)
    voice_app.state.voice_orchestrator = orchestrator
    client = TestClient(voice_app)

    with client.websocket_connect("/api/voice/stream") as websocket:
        websocket.send_json({"event": "start", "session_id": "sess", "user_id": "user"})
        ack = websocket.receive_json()
        assert ack["type"] == "session_ack"

        websocket.send_bytes(b"\x00" * 1600)
        first_transcript = websocket.receive_json()
        assert first_transcript["type"] == "transcript"

        websocket.send_json({"event": "stop"})
        payload = websocket.receive_json()
        last_transcript = None
        while payload.get("type") == "transcript":
            last_transcript = payload
            payload = websocket.receive_json()
        response_msg = payload
        assert response_msg["type"] == "response"
        assert response_msg["response_text"] == "respuesta sintetica"

        turn_complete = websocket.receive_json()
        assert turn_complete["type"] == "turn_complete"

    assert orchestrator.metrics.finished[-1][0] == "success"
    assert orchestrator._complete_calls[0]["transcript"] == "transcripcion final"


def test_voice_stream_max_duration_warning(voice_app):
    orchestrator = StubVoiceOrchestrator(max_seconds=1)
    voice_app.state.voice_orchestrator = orchestrator
    client = TestClient(voice_app)

    with client.websocket_connect("/api/voice/stream") as websocket:
        websocket.send_json({"event": "start", "session_id": "sess", "user_id": "user"})
        ack = websocket.receive_json()
        assert ack["type"] == "session_ack"

        # Send >1 second of PCM16 at 16kHz (32k bytes)
        websocket.send_bytes(b"\x00" * 40000)
        warning = websocket.receive_json()
        assert warning["type"] == "warning"
        assert "Duracion maxima" in warning["message"]

    assert orchestrator.metrics.finished
    result, reason = orchestrator.metrics.finished[-1]
    assert result == "warning"
    assert reason == "duration_exceeded"


def test_voice_config_reports_limits(voice_app):
    orchestrator = StubVoiceOrchestrator(max_seconds=45)
    voice_app.state.voice_orchestrator = orchestrator
    client = TestClient(voice_app)

    response = client.get("/api/voice/config")
    assert response.status_code == 200
    payload = response.json()
    assert payload["max_seconds"] == 45
    assert payload["sample_rate"] == orchestrator.settings.voice_stream_sample_rate


