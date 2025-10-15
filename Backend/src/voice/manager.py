"""Coordinator for voice streaming interactions."""
from __future__ import annotations

import base64
import time

from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, AsyncIterator, Optional, Protocol

from src.core.logging import get_logger
from src.observability.agent_metrics import record_error_event, record_turn_event
from src.domain.agents.agent_models import ResponseEnvelope
from src.voice.audio_models import TranscriptSegment, VoiceTurnResult
from src.voice.google_stt import GoogleSpeechClient
from src.voice.google_tts import GoogleTextToSpeechClient
from src.voice.elevenlabs_tts import ElevenLabsTextToSpeechClient
from src.voice.settings import VoiceSettings
from src.voice.storage import VoiceStorage
from src.voice import metrics as voice_metrics

logger = get_logger(__name__)


class TextToSpeechClient(Protocol):
    async def synthesize(
        self,
        *,
        text: str,
        language_code: Optional[str] = None,
        voice_name: Optional[str] = None,
        audio_encoding: Optional[str] = None,
        speaking_rate: float | None = None,
        pitch: float | None = None,
    ) -> tuple[str, str]:
        ...


@dataclass
class VoiceOrchestrator:
    orchestrator: Any
    settings: VoiceSettings
    speech: GoogleSpeechClient | None = None
    tts: TextToSpeechClient | None = None
    storage: VoiceStorage | None = None
    metrics: Any | None = None
    _turn_counters: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self.speech = self.speech or GoogleSpeechClient(self.settings)
        if self.tts is None:
            provider = (self.settings.tts_provider or "google").lower()
            if provider == "elevenlabs":
                if not (self.settings.elevenlabs_api_key and self.settings.elevenlabs_voice_id):
                    logger.warning(
                        {
                            "event": "voice_tts_disabled",
                            "provider": "elevenlabs",
                            "reason": "missing_api_key_or_voice_id",
                        }
                    )
                    self.tts = None
                else:
                    try:
                        self.tts = ElevenLabsTextToSpeechClient(self.settings)
                        logger.info({"event": "voice_tts_provider_selected", "provider": "elevenlabs"})
                    except Exception as exc:  # pragma: no cover - defensive
                        logger.warning(
                            {
                                "event": "voice_tts_disabled",
                                "provider": "elevenlabs",
                                "reason": "initialization_failed",
                                "error": str(exc),
                            }
                        )
                        self.tts = None
            elif provider == "google":
                try:
                    self.tts = GoogleTextToSpeechClient(self.settings)
                    logger.info({"event": "voice_tts_provider_selected", "provider": "google"})
                except Exception as exc:  # pragma: no cover - defensive
                    logger.warning(
                        {
                            "event": "voice_tts_disabled",
                            "provider": "google",
                            "reason": "initialization_failed",
                            "error": str(exc),
                        }
                    )
                    self.tts = None
            else:
                logger.warning(
                    {
                        "event": "voice_tts_disabled",
                        "provider": provider,
                        "reason": "unsupported_provider",
                    }
                )
                self.tts = None
        self.storage = self.storage or VoiceStorage(self.settings)
        self.metrics = self.metrics or voice_metrics

    async def stream_transcripts(
        self,
        audio_chunks: AsyncIterator[bytes | None],
        *,
        language_code: Optional[str] = None,
        sample_rate_hz: Optional[int] = None,
    ) -> AsyncGenerator[TranscriptSegment, None]:
        """Proxy STT streaming to Google client."""
        async for segment in self.speech.stream_transcribe(
            audio_chunks,
            language_code=language_code,
            sample_rate_hz=sample_rate_hz,
        ):
            yield segment

    async def complete_turn(
        self,
        *,
        transcript: str,
        session_id: str,
        user_id: str,
        trace_id: Optional[str] = None,
    ) -> VoiceTurnResult:
        """Send transcript to LangGraph and generate a spoken response."""
        if not transcript.strip():
            raise ValueError("Transcript is empty; cannot complete voice turn")

        turn_id = self._next_turn_id(session_id)
        started_at = time.perf_counter()
        metrics_token = None
        if self.metrics:
            try:
                metrics_token = self.metrics.voice_turn_started()
            except Exception:  # pragma: no cover - metrics should not break flow
                metrics_token = None
        logger.info({
            "event": "voice_turn_start",
            "session_id": session_id,
            "user_id": user_id,
            "trace_id": trace_id,
            "turn_id": turn_id,
        })

        try:
            envelope = await self._run_orchestrator(
                query=transcript,
                session_id=session_id,
                user_id=user_id,
                trace_id=trace_id,
            )
        except Exception as exc:
            if self.metrics and metrics_token is not None:
                try:
                    self.metrics.voice_turn_failed(metrics_token)
                except Exception:  # pragma: no cover - metrics must not break flow
                    pass
            self._record_error(
                session_id=session_id,
                turn_id=turn_id,
                error_code="orchestrator_failure",
                error_message=str(exc),
                user_id=user_id,
                trace_id=trace_id,
            )
            raise

        response_text = self._extract_response_text(envelope)
        audio_b64: str = ""
        mime_type: str = "audio/mpeg"
        if self.tts is None:
            logger.info(
                {
                    "event": "voice_tts_skipped",
                    "reason": "provider_unavailable",
                    "session_id": session_id,
                    "turn_id": turn_id,
                }
            )
        else:
            try:
                audio_b64, mime_type = await self.tts.synthesize(text=response_text)
            except Exception as exc:
                logger.warning(
                    {
                        "event": "voice_tts_failure",
                        "error": str(exc),
                        "session_id": session_id,
                        "turn_id": turn_id,
                    }
                )
                audio_b64 = ""
                if self.metrics and metrics_token is not None:
                    try:
                        self.metrics.voice_turn_failed(metrics_token)
                    except Exception:  # pragma: no cover - best effort
                        pass
                self._record_error(
                    session_id=session_id,
                    turn_id=turn_id,
                    error_code="tts_failure",
                    error_message=str(exc),
                    user_id=user_id,
                    trace_id=trace_id,
                )

        audio_bytes = base64.b64decode(audio_b64.encode("ascii")) if audio_b64 else b""
        audio_url = None
        if audio_bytes:
            try:
                audio_url = await self.storage.persist(audio_bytes, prefix=session_id)
            except Exception as exc:
                if self.metrics and metrics_token is not None:
                    try:
                        self.metrics.voice_turn_failed(metrics_token)
                    except Exception:  # pragma: no cover - metrics must not break flow
                        pass
                self._record_error(
                    session_id=session_id,
                    turn_id=turn_id,
                    error_code="storage_failure",
                    error_message=str(exc),
                    user_id=user_id,
                    trace_id=trace_id,
                )
                raise

        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        response_type_value = getattr(envelope, "response_type", None)
        result = VoiceTurnResult(
            transcript=transcript,
            response_text=response_text,
            response_audio_base64=audio_b64,
            response_audio_mime=mime_type,
            audio_url=audio_url,
            metadata={
                "trace_id": getattr(envelope, "trace_id", trace_id),
                "response_type": response_type_value.name if response_type_value else None,
                "channel": "voice",
                "audio_url": audio_url,
                "transcript": transcript,
            },
        )

        self._record_metrics(
            envelope=envelope,
            session_id=session_id,
            user_id=user_id,
            turn_id=turn_id,
            latency_ms=elapsed_ms,
            transcript=transcript,
            audio_url=audio_url,
        )

        if self.metrics and metrics_token is not None:
            try:
                self.metrics.voice_turn_completed(metrics_token)
            except Exception:  # pragma: no cover - metrics must not break flow
                pass

        logger.info({
            "event": "voice_turn_complete",
            "session_id": session_id,
            "user_id": user_id,
            "trace_id": trace_id or result.metadata.get("trace_id") if result.metadata else None,
            "turn_id": turn_id,
            "latency_ms": elapsed_ms,
        })
        return result

    def _next_turn_id(self, session_id: str) -> int:
        counter = self._turn_counters.get(session_id, 0) + 1
        self._turn_counters[session_id] = counter
        return counter

    def _record_metrics(
        self,
        *,
        envelope: ResponseEnvelope,
        session_id: str,
        user_id: str,
        turn_id: int,
        latency_ms: int,
        transcript: str,
        audio_url: str | None,
    ) -> None:
        response_type_value = getattr(envelope, 'response_type', None)
        response_type_name = getattr(response_type_value, 'name', None) if response_type_value else None
        success = (response_type_name or '').lower() != 'error'
        metadata = {
            'channel': 'voice',
            'transcript': transcript,
            'audio_url': audio_url,
        }
        meta_src = getattr(envelope, 'meta', None)
        if isinstance(meta_src, dict):
            for key, value in meta_src.items():
                metadata.setdefault(key, value)
        record_turn_event(
            agent_name=getattr(envelope, 'intent', None) or 'voice_orchestrator',
            session_id=session_id,
            turn_id=turn_id,
            latency_ms=latency_ms,
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            user_id=user_id,
            channel='voice',
            trace_id=getattr(envelope, 'trace_id', None),
            response_type=response_type_name,
            success=success,
            metadata=metadata,
        )

    def _record_error(
        self,
        *,
        session_id: str,
        turn_id: int,
        error_code: str,
        error_message: str,
        user_id: str,
        trace_id: str | None,
    ) -> None:
        logger.error({
            'event': 'voice_turn_error',
            'session_id': session_id,
            'turn_id': turn_id,
            'error_code': error_code,
            'error_message': error_message,
            'trace_id': trace_id,
            'user_id': user_id,
        })
        record_error_event(
            agent_name='voice_orchestrator',
            session_id=session_id,
            turn_id=turn_id,
            error_code=error_code,
            error_message=error_message,
            user_id=user_id,
            channel='voice',
            trace_id=trace_id,
        )

    async def _run_orchestrator(
        self,
        *,
        query: str,
        session_id: str,
        user_id: str,
        trace_id: Optional[str],
    ) -> ResponseEnvelope:
        orchestrator = getattr(self, "orchestrator", None)
        if orchestrator is None or not hasattr(orchestrator, "process_query"):
            raise RuntimeError("LangGraph orchestrator not initialised")

        envelope = await orchestrator.process_query(
            query=query,
            session_id=session_id,
            user_id=user_id,
            trace_id=trace_id,
            channel='voice',
        )
        return envelope

    @staticmethod
    def _extract_response_text(envelope: ResponseEnvelope) -> str:
        if getattr(envelope, "message", None):
            return envelope.message
        if isinstance(getattr(envelope, "data", None), dict):
            candidate = envelope.data.get("response") or envelope.data.get("text")
            if isinstance(candidate, str) and candidate.strip():
                return candidate
        return "No se encontro una respuesta para sintetizar."
