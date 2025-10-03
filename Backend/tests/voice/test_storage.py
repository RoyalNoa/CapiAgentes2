import asyncio
from pathlib import Path

import pytest

from src.voice.settings import VoiceSettings
from src.voice.storage import VoiceStorage


@pytest.mark.asyncio
async def test_voice_storage_local_writes_file(tmp_path, monkeypatch):
    monkeypatch.setenv('VOICE_STREAM_STORAGE_DIR', str(tmp_path))
    monkeypatch.delenv('VOICE_STREAM_BUCKET', raising=False)

    settings = VoiceSettings()
    storage = VoiceStorage(settings)

    audio_bytes = b'\x00\x01\x02\x03'
    result_path = await storage.persist(audio_bytes, prefix='unit_test')

    assert result_path is not None
    saved_path = Path(result_path)
    assert saved_path.exists()
    assert saved_path.read_bytes() == audio_bytes
