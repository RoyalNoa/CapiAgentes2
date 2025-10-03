"""Voice streaming endpoints for Google Cloud STT/TTS integration."""
from __future__ import annotations

import asyncio
import json
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Dict, List, Union
from uuid import uuid4

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse

from src.core.logging import get_logger
from src.voice.audio_models import TranscriptSegment
from src.voice.manager import VoiceOrchestrator

router = APIRouter(prefix="/api/voice", tags=["voice"])
logger = get_logger(__name__)


@dataclass
class _StreamLimitTracker:
    sample_rate_hz: int
    max_seconds: int
    total_bytes: int = 0

    def register(self, byte_length: int) -> float:
        self.total_bytes += byte_length
        if self.sample_rate_hz <= 0:
            return 0.0
        samples = self.total_bytes / 2
        return samples / float(self.sample_rate_hz)

    def is_limit_exceeded(self, duration_seconds: float) -> bool:
        return self.max_seconds > 0 and duration_seconds > float(self.max_seconds)


def _get_voice_orchestrator(scope_obj: Union[Request, WebSocket]) -> VoiceOrchestrator:
    app = getattr(scope_obj, "app", None)
    manager = getattr(getattr(app, "state", None), "voice_orchestrator", None)
    if manager is None:
        raise HTTPException(status_code=503, detail="Voice orchestrator not initialised")
    return manager


@router.get("/config")
async def voice_config(request: Request) -> Dict[str, Any]:
    """Expose non-sensitive configuration for health checks."""
    manager = _get_voice_orchestrator(request)
    settings = manager.settings
    return {
        "language": settings.google_speech_language,
        "tts_voice": settings.google_tts_voice,
        "sample_rate": settings.voice_stream_sample_rate,
        "chunk_ms": settings.voice_stream_chunk_ms,
        "bucket_configured": bool(settings.voice_stream_bucket),
        "storage_dir": settings.voice_stream_storage_dir,
        "max_seconds": settings.voice_stream_max_seconds,
    }


@router.websocket("/stream")
async def voice_stream(websocket: WebSocket) -> None:
    """Bidirectional WebSocket: receives audio frames and returns transcripts + spoken reply."""
    await websocket.accept()
    orchestrator = _get_voice_orchestrator(websocket)
    settings = orchestrator.settings

    try:
        while True:
            start_payload = await _receive_json(websocket)
            if start_payload.get("event") != "start":
                await websocket.send_json({"type": "error", "message": "Expected start event"})
                continue

            session_id = str(start_payload.get("session_id") or websocket.query_params.get("session_id") or uuid4())
            user_id = str(start_payload.get("user_id") or websocket.query_params.get("user_id") or "anonymous")
            trace_id = str(start_payload.get("trace_id") or uuid4())
            language = str(start_payload.get("language") or websocket.query_params.get("language") or settings.google_speech_language)
            sample_rate = int(start_payload.get("sample_rate") or websocket.query_params.get("sample_rate") or settings.voice_stream_sample_rate)

            metrics_module = getattr(orchestrator, "metrics", None)
            metrics_ctx = None
            final_result = "success"
            warning_reason: str | None = None
            limit_seconds = int(getattr(settings, "voice_stream_max_seconds", 0) or 0)

            if metrics_module:
                try:
                    metrics_ctx = metrics_module.stream_started(
                        session_id=session_id,
                        user_id=user_id,
                        sample_rate_hz=sample_rate,
                        limit_seconds=limit_seconds,
                    )
                except Exception:  # pragma: no cover - metrics must never break the stream
                    metrics_ctx = None

            tracker = _StreamLimitTracker(
                sample_rate_hz=sample_rate or settings.voice_stream_sample_rate,
                max_seconds=limit_seconds,
            )

            await websocket.send_json({
                "type": "session_ack",
                "session_id": session_id,
                "user_id": user_id,
                "trace_id": trace_id,
                "language": language,
                "sample_rate": sample_rate,
            })

            transcript_segments: List[str] = []
            audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=64)
            stream_complete = asyncio.Event()

            async def audio_generator() -> Any:
                try:
                    while True:
                        chunk = await audio_queue.get()
                        audio_queue.task_done()
                        if chunk is None:
                            break
                        yield chunk
                finally:
                    stream_complete.set()

            async def consume_transcripts() -> None:
                try:
                    async for segment in orchestrator.stream_transcripts(
                        audio_generator(),
                        language_code=language,
                        sample_rate_hz=sample_rate,
                    ):
                        await _dispatch_segment(websocket, segment)
                        if segment.is_final and segment.text.strip():
                            transcript_segments.append(segment.text.strip())
                except Exception as exc:  # pragma: no cover - defensive logging
                    logger.exception("Error durante la transcripcion de voz", extra={"error": str(exc)})
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    raise

            transcript_task = asyncio.create_task(consume_transcripts())

            try:
                limit_reached = False
                try:
                    limit_reached = await _forward_audio_frames(
                        websocket,
                        audio_queue,
                        tracker,
                        metrics_module=metrics_module,
                        metrics_ctx=metrics_ctx,
                    )
                except WebSocketDisconnect:
                    final_result = "error"
                    raise
                except Exception as exc:  # pragma: no cover - defensive logging
                    final_result = "error"
                    await websocket.send_json({"type": "error", "message": str(exc)})
                    raise
                finally:
                    await audio_queue.put(None)
                    await stream_complete.wait()
                    with suppress(Exception):
                        await transcript_task

                if limit_reached:
                    final_result = "warning"
                    warning_reason = "duration_exceeded"
                    await websocket.send_json({"type": "warning", "message": "Duracion maxima de audio excedida"})
                    continue

                final_transcript = " ".join(transcript_segments).strip()
                if not final_transcript:
                    final_result = "warning"
                    warning_reason = "empty_transcript"
                    await websocket.send_json({"type": "warning", "message": "No se detecto audio para transcribir"})
                    continue

                try:
                    voice_result = await orchestrator.complete_turn(
                        transcript=final_transcript,
                        session_id=session_id,
                        user_id=user_id,
                        trace_id=trace_id,
                    )
                except Exception as exc:  # pragma: no cover - orchestrator failure
                    final_result = "error"
                    logger.exception("Voice turn failed", extra={"session_id": session_id, "error": str(exc)})
                    await websocket.send_json({"type": "error", "message": f"No se pudo generar la respuesta: {exc}"})
                    continue

                await websocket.send_json({
                    "type": "response",
                    "session_id": session_id,
                    "trace_id": trace_id,
                    "transcript": voice_result.transcript,
                    "response_text": voice_result.response_text,
                    "audio": {
                        "base64": voice_result.response_audio_base64,
                        "mime_type": voice_result.response_audio_mime,
                        "url": voice_result.audio_url,
                    },
                    "metadata": voice_result.metadata or {},
                })
                await websocket.send_json({"type": "turn_complete"})
            finally:
                if metrics_module and metrics_ctx:
                    with suppress(Exception):
                        metrics_module.stream_finished(metrics_ctx, result=final_result, warning_reason=warning_reason)
    except WebSocketDisconnect:
        logger.info({"event": "voice_stream_disconnect", "client": str(websocket.client)})
    except Exception as exc:  # pragma: no cover - top-level defensive guard
        logger.exception("Unhandled voice stream error", extra={"error": str(exc)})
        await websocket.close(code=1011, reason=str(exc))





async def _forward_audio_frames(
    websocket: WebSocket,
    queue: asyncio.Queue[bytes | None],
    tracker: _StreamLimitTracker,
    *,
    metrics_module: Any | None = None,
    metrics_ctx: Any | None = None,
) -> bool:
    """Relay binary frames from websocket to STT queue until stop event."""
    while True:
        message = await websocket.receive()
        if message.get("type") == "websocket.disconnect":
            raise WebSocketDisconnect()
        if message.get("bytes") is not None:
            chunk = message["bytes"]
            if metrics_module and metrics_ctx:
                with suppress(Exception):
                    metrics_module.stream_frame_received(metrics_ctx, bytes_length=len(chunk))
            duration = tracker.register(len(chunk))
            if tracker.is_limit_exceeded(duration):
                return True
            await queue.put(chunk)
            continue
        if message.get("text") is not None:
            payload = json.loads(message["text"])
            if payload.get("event") == "stop":
                break
            if payload.get("event") == "ping":
                await websocket.send_json({"type": "pong"})
                continue
            # Ignore unknown textual events to keep stream active
            continue
    return False


async def _dispatch_segment(websocket: WebSocket, segment: TranscriptSegment) -> None:
    payload: Dict[str, Any] = {
        "type": "transcript",
        "text": segment.text,
        "is_final": segment.is_final,
    }
    if segment.stability is not None:
        payload["stability"] = segment.stability
    if segment.confidence is not None:
        payload["confidence"] = segment.confidence
    await websocket.send_json(payload)


async def _receive_json(websocket: WebSocket) -> Dict[str, Any]:
    message = await websocket.receive()
    if message.get("type") == "websocket.disconnect":
        raise WebSocketDisconnect()
    text = message.get("text")
    if text is None:
        return {}
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}

