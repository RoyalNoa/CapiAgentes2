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
    await websocket.accept()
    orchestrator = _get_voice_orchestrator(websocket)
    settings = orchestrator.settings

    try:
        ...
