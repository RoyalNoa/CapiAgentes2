"""Storage helpers for synthesized audio."""
from __future__ import annotations

import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.core.logging import get_logger
from src.voice.settings import VoiceSettings

try:  # Optional dependency; only required when bucket configured
    from google.cloud import storage as gcs  # type: ignore
except ImportError:  # pragma: no cover
    gcs = None

logger = get_logger(__name__)


class VoiceStorage:
    """Persist synthesized audio to filesystem or Google Cloud Storage."""

    def __init__(self, settings: VoiceSettings) -> None:
        self._settings = settings
        self._bucket = None
        self._client = None
        bucket_name = (settings.voice_stream_bucket or "").strip()
        if bucket_name:
            if not gcs:
                logger.warning(
                    {
                        "event": "voice_storage_bucket_disabled",
                        "reason": "missing_google_cloud_storage",
                        "bucket": bucket_name,
                    }
                )
                # Fallback to filesystem storage when dependency is unavailable.
                settings.voice_stream_bucket = None  # type: ignore[attr-defined]
                bucket_name = ""
            else:
                if bucket_name.startswith("gs://"):
                    bucket_name = bucket_name.replace("gs://", "", 1)
                self._client = gcs.Client(project=settings.gcp_project_id or None)
                self._bucket = self._client.bucket(bucket_name)

        if not bucket_name:
            settings.ensure_storage_dir()

    async def persist(self, audio_bytes: bytes, *, prefix: str = "voice") -> Optional[str]:
        """Persist audio and return accessible URL when available."""
        if not audio_bytes:
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S%f")
        filename = f"{prefix}_{timestamp}.mp3"

        if self._bucket and self._client:
            blob = self._bucket.blob(filename)

            def _upload() -> None:
                blob.upload_from_string(audio_bytes, content_type="audio/mpeg")
                if not blob.public_url:
                    blob.make_public()

            await asyncio.get_running_loop().run_in_executor(None, _upload)
            logger.info({"event": "voice_audio_uploaded", "bucket": self._bucket.name, "blob": filename})
            return blob.public_url

        # Fallback to filesystem
        target_dir = Path(self._settings.voice_stream_storage_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / filename
        file_path.write_bytes(audio_bytes)
        logger.info({"event": "voice_audio_saved", "path": str(file_path)})
        return str(file_path)
