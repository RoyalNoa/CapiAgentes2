"""Google Cloud Speech-to-Text async streaming helper."""
from __future__ import annotations

import asyncio
from typing import AsyncIterator, AsyncGenerator

from google.api_core.exceptions import GoogleAPIError
from google.cloud.speech_v1 import SpeechAsyncClient
from google.cloud.speech_v1.types import (
    RecognitionConfig,
    StreamingRecognitionConfig,
    StreamingRecognizeRequest,
)

from src.core.logging import get_logger
from src.voice.audio_models import TranscriptSegment
from src.voice.settings import VoiceSettings

logger = get_logger(__name__)


class GoogleSpeechClient:
    """Thin wrapper around Google Cloud streaming STT."""

    def __init__(self, settings: VoiceSettings) -> None:
        self._settings = settings

    async def stream_transcribe(
        self,
        audio_chunks: AsyncIterator[bytes | None],
        *,
        language_code: str | None = None,
        sample_rate_hz: int | None = None,
        profanity_filter: bool = False,
        enable_automatic_punctuation: bool = True,
    ) -> AsyncGenerator[TranscriptSegment, None]:
        """Yield transcript segments as they are produced by Google STT.

        Args:
            audio_chunks: asynchronous iterator yielding raw audio chunks (PCM 16-bit little endian).
            language_code: optional language override; defaults to configured language.
            sample_rate_hz: audio sampling rate; defaults to configured rate.
            profanity_filter: whether to mask profanity.
            enable_automatic_punctuation: toggle punctuation insertion.
        """

        language = language_code or self._settings.google_speech_language
        sample_rate = sample_rate_hz or self._settings.voice_stream_sample_rate

        recognition_config = RecognitionConfig(
            encoding=RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=language,
            sample_rate_hertz=sample_rate,
            enable_automatic_punctuation=enable_automatic_punctuation,
            profanity_filter=profanity_filter,
            enable_word_time_offsets=False,
        )
        streaming_config = StreamingRecognitionConfig(
            config=recognition_config,
            interim_results=True,
            single_utterance=False,
        )

        async def request_iterator() -> AsyncGenerator[StreamingRecognizeRequest, None]:
            yield StreamingRecognizeRequest(streaming_config=streaming_config)
            async for chunk in audio_chunks:
                if chunk is None:
                    break
                if not chunk:
                    continue
                yield StreamingRecognizeRequest(audio_content=chunk)

        try:
            async with SpeechAsyncClient() as client:
                responses = await client.streaming_recognize(requests=request_iterator())
                async for response in responses:
                    for result in response.results:
                        if not result.alternatives:
                            continue
                        alternative = result.alternatives[0]
                        segment = TranscriptSegment(
                            text=alternative.transcript or "",
                            is_final=result.is_final,
                            stability=getattr(result, "stability", None),
                            confidence=getattr(alternative, "confidence", None),
                        )
                        yield segment
        except GoogleAPIError as exc:
            logger.exception("Google STT streaming error", extra={"error": str(exc)})
            raise
