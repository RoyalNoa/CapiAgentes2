"""Typed models shared across the voice pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class TranscriptSegment:
    text: str
    is_final: bool
    stability: float | None = None
    confidence: float | None = None


@dataclass
class VoiceTurnResult:
    transcript: str
    response_text: str
    response_audio_base64: str | None
    response_audio_mime: str | None
    audio_url: Optional[str] = None
    metadata: dict[str, str | float | int | bool | None] | None = None
