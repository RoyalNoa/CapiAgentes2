"""Centralised configuration for voice streaming services."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VoiceSettings:
    """Runtime configuration for Google Cloud voice services."""

    google_application_credentials: str | None = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    gcp_project_id: str | None = os.getenv("GCP_PROJECT_ID")
    gcp_region: str | None = os.getenv("GCP_REGION")
    google_speech_language: str = os.getenv("GOOGLE_SPEECH_LANGUAGE", "es-ES")
    google_tts_voice: str = os.getenv("GOOGLE_TTS_VOICE", "es-ES-Wavenet-D")
    google_tts_audio_encoding: str = os.getenv("GOOGLE_TTS_AUDIO_ENCODING", "MP3")
    voice_stream_bucket: str | None = os.getenv("VOICE_STREAM_BUCKET")
    voice_stream_storage_dir: str = os.getenv("VOICE_STREAM_STORAGE_DIR", "/app/tmp/voice")
    voice_stream_sample_rate: int = int(os.getenv("VOICE_STREAM_SAMPLE_RATE", "16000"))
    voice_stream_chunk_ms: int = int(os.getenv("VOICE_STREAM_CHUNK_MS", "100"))
    voice_stream_max_seconds: int = int(os.getenv("VOICE_STREAM_MAX_SECONDS", "300"))

    def ensure_storage_dir(self) -> None:
        """Create local storage directory when using filesystem persistence."""
        if self.voice_stream_bucket:
            return
        os.makedirs(self.voice_stream_storage_dir, exist_ok=True)
