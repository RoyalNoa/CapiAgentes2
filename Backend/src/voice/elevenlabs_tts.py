"""ElevenLabs Text-to-Speech helper."""
from __future__ import annotations

import base64
import json
from typing import Any, Dict, Optional

import httpx

from src.core.logging import get_logger
from src.voice.settings import VoiceSettings

logger = get_logger(__name__)


class ElevenLabsTextToSpeechClient:
    """Encapsulates ElevenLabs Text-to-Speech synthesis."""

    def __init__(self, settings: VoiceSettings) -> None:
        self._settings = settings
        if not self._settings.elevenlabs_api_key:
            raise ValueError("ElevenLabs API key is not configured")

    async def synthesize(
        self,
        *,
        text: str,
        voice_name: Optional[str] = None,
        language_code: Optional[str] = None,
        audio_encoding: Optional[str] = None,
        speaking_rate: float | None = None,
        pitch: float | None = None,
    ) -> tuple[str, str]:
        """Generate speech audio using ElevenLabs."""
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")

        voice_id = voice_name or self._settings.elevenlabs_voice_id
        if not voice_id:
            raise ValueError("ElevenLabs voice ID is not configured")

        headers = {
            "xi-api-key": self._settings.elevenlabs_api_key or "",
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
        }

        url = f"{self._settings.elevenlabs_base_url.rstrip('/')}/v1/text-to-speech/{voice_id}"
        payload = self._build_payload(
            text=text,
            model_id=self._settings.elevenlabs_model_id,
            language_code=language_code,
            audio_encoding=audio_encoding,
        )

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            detail = response.text
            logger.error(
                "ElevenLabs TTS synthesis failed",
                extra={"status_code": response.status_code, "detail": detail},
            )
            raise RuntimeError(f"ElevenLabs TTS request failed: {response.status_code} {detail}")

        audio_bytes = response.content
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        mime_type = response.headers.get("Content-Type", "audio/mpeg")
        return audio_b64, mime_type

    def _build_payload(
        self,
        *,
        text: str,
        model_id: str,
        language_code: Optional[str],
        audio_encoding: Optional[str],
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "text": text,
            "model_id": model_id,
        }

        settings = self._parse_voice_settings(self._settings.elevenlabs_voice_settings)
        if settings:
            payload["voice_settings"] = settings

        if language_code:
            payload["language_code"] = language_code
        if audio_encoding:
            payload["output_format"] = audio_encoding

        return payload

    @staticmethod
    def _parse_voice_settings(raw_settings: Optional[str]) -> Dict[str, Any]:
        if not raw_settings:
            return {}
        try:
            parsed = json.loads(raw_settings)
        except json.JSONDecodeError:
            logger.warning("Invalid ELEVENLABS_VOICE_SETTINGS JSON; ignoring value")
            return {}
        if not isinstance(parsed, dict):
            logger.warning("ELEVENLABS_VOICE_SETTINGS must be a JSON object; ignoring value")
            return {}
        return parsed
