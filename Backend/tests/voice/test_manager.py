import sys
import types

if 'google' not in sys.modules:
    google_pkg = types.ModuleType('google')
    sys.modules['google'] = google_pkg

    api_core_mod = types.ModuleType('google.api_core')
    sys.modules['google.api_core'] = api_core_mod

    exceptions_mod = types.ModuleType('google.api_core.exceptions')
    class GoogleAPIError(Exception):
        pass
    exceptions_mod.GoogleAPIError = GoogleAPIError
    sys.modules['google.api_core.exceptions'] = exceptions_mod

    cloud_mod = types.ModuleType('google.cloud')
    sys.modules['google.cloud'] = cloud_mod

    speech_mod = types.ModuleType('google.cloud.speech_v1')
    class DummySpeechAsyncClient:
        async def streaming_recognize(self, requests):
            async def _gen():
                if False:
                    yield None
            return _gen()

        async def close(self):
            pass
    speech_mod.SpeechAsyncClient = DummySpeechAsyncClient
    sys.modules['google.cloud.speech_v1'] = speech_mod


    speech_types_mod = types.ModuleType('google.cloud.speech_v1.types')
    class RecognitionConfig:
        class AudioEncoding:
            LINEAR16 = 'LINEAR16'
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    class StreamingRecognitionConfig:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)
    class StreamingRecognizeRequest:
        def __init__(self, streaming_config=None, audio_content=None):
            self.streaming_config = streaming_config
            self.audio_content = audio_content
    speech_types_mod.RecognitionConfig = RecognitionConfig
    speech_types_mod.StreamingRecognitionConfig = StreamingRecognitionConfig
    speech_types_mod.StreamingRecognizeRequest = StreamingRecognizeRequest
    sys.modules['google.cloud.speech_v1.types'] = speech_types_mod

    tts_mod = types.ModuleType('google.cloud.texttospeech_v1')
    class DummyTextToSpeechAsyncClient:
        async def synthesize_speech(self, input, voice, audio_config):
            class _Response:
                audio_content = b'voice-bytes'
            return _Response()

        async def close(self):
            pass
    tts_mod.TextToSpeechAsyncClient = DummyTextToSpeechAsyncClient
    sys.modules['google.cloud.texttospeech_v1'] = tts_mod

    types_mod = types.ModuleType('google.cloud.texttospeech_v1.types')
    class AudioEncoding:
        MP3 = 'MP3'
    class AudioConfig:
        AudioEncoding = AudioEncoding
        def __init__(self, audio_encoding, speaking_rate=1.0, pitch=0.0):
            self.audio_encoding = audio_encoding
            self.speaking_rate = speaking_rate
            self.pitch = pitch
    class SynthesisInput:
        def __init__(self, text):
            self.text = text
    class VoiceSelectionParams:
        def __init__(self, language_code, name):
            self.language_code = language_code
            self.name = name
    types_mod.AudioEncoding = AudioEncoding
    types_mod.AudioConfig = AudioConfig
    types_mod.SynthesisInput = SynthesisInput
    types_mod.VoiceSelectionParams = VoiceSelectionParams
    tts_mod.types = types_mod
    sys.modules['google.cloud.texttospeech_v1.types'] = types_mod
import base64
from typing import Any

import pytest

from src.domain.agents.agent_models import ResponseEnvelope, ResponseType
from src.domain.contracts.intent import IntentType
from src.voice.manager import VoiceOrchestrator
from src.voice.settings import VoiceSettings



def make_envelope(message: str = 'hola voz') -> ResponseEnvelope:
    return ResponseEnvelope(
        trace_id='trace-1',
        response_type=ResponseType.SUCCESS,
        intent=IntentType.SMALL_TALK,
        message=message,
        data={},
        meta={'model': 'gpt', 'latency_ms': 42},
    )


class StubOrchestrator:
    def __init__(self, envelope: ResponseEnvelope) -> None:
        self.envelope = envelope
        self.calls: list[dict[str, Any]] = []

    async def process_query(self, *, query: str, session_id: str, user_id: str, trace_id: str | None, channel: str | None = None) -> ResponseEnvelope:
        self.calls.append({'query': query, 'session_id': session_id, 'user_id': user_id, 'trace_id': trace_id, 'channel': channel})
        return self.envelope


class StubTTS:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def synthesize(self, *, text: str, **_: Any) -> tuple[str, str]:
        self.calls.append({'text': text})
        return base64.b64encode(b'voice-bytes').decode('ascii'), 'audio/mpeg'




class StubMetrics:
    def __init__(self) -> None:
        self.started = 0
        self.completed = 0
        self.failed = 0

    def voice_turn_started(self) -> float:
        self.started += 1
        return 0.0

    def voice_turn_completed(self, token: float) -> None:
        self.completed += 1

    def voice_turn_failed(self, token: float) -> None:
        self.failed += 1

class StubStorage:
    def __init__(self) -> None:
        self.persist_calls: list[bytes] = []

    async def persist(self, audio_bytes: bytes, *, prefix: str = 'voice') -> str:
        self.persist_calls.append(audio_bytes)
        return f'/tmp/{prefix}.mp3'


@pytest.mark.asyncio
async def test_voice_orchestrator_records_turn(monkeypatch):
    events: list[dict[str, Any]] = []

    def fake_record_turn_event(**payload: Any) -> None:
        events.append(payload)

    errors: list[dict[str, Any]] = []

    def fake_record_error_event(**payload: Any) -> None:
        errors.append(payload)

    monkeypatch.setattr('src.voice.manager.record_turn_event', fake_record_turn_event)
    monkeypatch.setattr('src.voice.manager.record_error_event', fake_record_error_event)

    settings = VoiceSettings()
    orchestrator = StubOrchestrator(make_envelope())
    tts = StubTTS()
    storage = StubStorage()
    metrics = StubMetrics()

    voice = VoiceOrchestrator(
        orchestrator=orchestrator,
        settings=settings,
        tts=tts,
        storage=storage,
        metrics=metrics,
    )

    result = await voice.complete_turn(transcript='hola agente', session_id='sess-1', user_id='user-1')

    assert result.response_text == 'hola voz'
    assert result.audio_url == '/tmp/sess-1.mp3'
    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0]['channel'] == 'voice'
    assert tts.calls[0]['text'] == 'hola voz'
    assert storage.persist_calls[0] == b'voice-bytes'
    assert metrics.started == 1
    assert metrics.completed == 1
    assert metrics.failed == 0
    assert errors == []
    assert events and events[0]['channel'] == 'voice'
    assert events[0]['session_id'] == 'sess-1'
    assert events[0]['turn_id'] == 1
    assert events[0]['metadata']['transcript'] == 'hola agente'


@pytest.mark.asyncio
async def test_voice_orchestrator_records_errors(monkeypatch):
    errors: list[dict[str, Any]] = []

    def fake_record_error_event(**payload: Any) -> None:
        errors.append(payload)

    monkeypatch.setattr('src.voice.manager.record_turn_event', lambda **_: None)
    monkeypatch.setattr('src.voice.manager.record_error_event', fake_record_error_event)

    class FailingTTS(StubTTS):
        async def synthesize(self, *, text: str, **_: Any) -> tuple[str, str]:
            raise RuntimeError('boom')

    metrics = StubMetrics()
    voice = VoiceOrchestrator(
        orchestrator=StubOrchestrator(make_envelope()),
        settings=VoiceSettings(),
        tts=FailingTTS(),
        storage=StubStorage(),
        metrics=metrics,
    )

    result = await voice.complete_turn(transcript='hola', session_id='sess-err', user_id='user-err')

    assert result.response_audio_base64 == ""
    assert result.audio_url is None
    assert metrics.started == 1
    assert metrics.failed == 1
    assert metrics.completed == 1
    assert errors and errors[0]['error_code'] == 'tts_failure'




