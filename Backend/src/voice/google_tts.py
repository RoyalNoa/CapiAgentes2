"""Google Cloud Text-to-Speech helper."""
from __future__ import annotations

import base64
import inspect
from importlib import import_module
from typing import Any, Optional, Type

from google.api_core.exceptions import GoogleAPIError

from src.core.logging import get_logger
from src.voice.settings import VoiceSettings

logger = get_logger(__name__)


class GoogleTextToSpeechClient:
    """Encapsulates Google Cloud Text-to-Speech synthesis."""

    def __init__(self, settings: VoiceSettings) -> None:
        self._settings = settings
        self._client_cls: Type[Any] | None = None
        self._synthesis_input_cls: Type[Any] | None = None
        self._voice_selection_cls: Type[Any] | None = None
        self._audio_config_cls: Type[Any] | None = None
        self._audio_encoding_enum: Any = None

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
        """Generate speech audio.

        Returns:
            Tuple with base64-encoded audio content and MIME type string.
        """
        if not text.strip():
            raise ValueError("Cannot synthesize empty text")

        self._ensure_components()

        language = language_code or self._settings.google_speech_language
        voice = voice_name or self._settings.google_tts_voice
        encoding_name = (audio_encoding or self._settings.google_tts_audio_encoding).upper()
        mime_type = self._resolve_mime_type(encoding_name)

        synthesis_input = self._synthesis_input_cls(text=text)
        voice_params = self._voice_selection_cls(language_code=language, name=voice)
        audio_encoding_value = self._resolve_audio_encoding(encoding_name)

        audio_config = self._audio_config_cls(
            audio_encoding=audio_encoding_value,
            speaking_rate=speaking_rate or 1.0,
            pitch=pitch or 0.0,
        )

        client = self._client_cls()

        try:
            if hasattr(client, "__aenter__") and hasattr(client, "__aexit__"):
                async with client as session:
                    response = await session.synthesize_speech(
                        input=synthesis_input,
                        voice=voice_params,
                        audio_config=audio_config,
                    )
            else:
                response = await client.synthesize_speech(
                    input=synthesis_input,
                    voice=voice_params,
                    audio_config=audio_config,
                )
        except GoogleAPIError as exc:
            logger.exception("Google TTS synthesis error", extra={"error": str(exc)})
            raise
        finally:
            if not hasattr(client, "__aenter__"):
                close = getattr(client, "close", None)
                if callable(close):
                    result = close()
                    if inspect.iscoroutine(result):
                        await result

        audio_content = getattr(response, "audio_content", None) or b""
        audio_b64 = base64.b64encode(audio_content)
        return audio_b64.decode("ascii"), mime_type

    def _ensure_components(self) -> None:
        if self._client_cls is not None:
            return

        module: Any | None = None
        module_name = ""
        last_error: Exception | None = None
        for module_name in ("google.cloud.texttospeech_v1", "google.cloud.texttospeech"):
            try:
                module = import_module(module_name)
                break
            except ImportError as exc:  # pragma: no cover - executed in environments without the SDK
                last_error = exc
        if module is None:
            raise RuntimeError(
                "google-cloud-texttospeech is required to synthesize audio. Install google-cloud-texttospeech."
            ) from last_error

        types_module = getattr(module, "types", None)
        if types_module is None:
            try:
                types_module = import_module(f"{module_name}.types")
            except ImportError:
                types_module = module

        client_cls = getattr(module, "TextToSpeechAsyncClient", None)
        if client_cls is None:
            raise RuntimeError("TextToSpeechAsyncClient is not available in the Google TTS module.")

        def _resolve(name: str) -> Any:
            attr = getattr(module, name, None)
            if attr is None and types_module is not module:
                attr = getattr(types_module, name, None)
            return attr

        synthesis_input_cls = _resolve("SynthesisInput")
        voice_selection_cls = _resolve("VoiceSelectionParams")
        audio_config_cls = _resolve("AudioConfig")

        if not (synthesis_input_cls and voice_selection_cls and audio_config_cls):
            raise RuntimeError("Google TTS types are missing required definitions.")

        audio_enum = getattr(types_module, "AudioEncoding", None)
        if audio_enum is None and hasattr(audio_config_cls, "AudioEncoding"):
            audio_enum = getattr(audio_config_cls, "AudioEncoding")

        self._client_cls = client_cls
        self._synthesis_input_cls = synthesis_input_cls
        self._voice_selection_cls = voice_selection_cls
        self._audio_config_cls = audio_config_cls
        self._audio_encoding_enum = audio_enum

    def _resolve_audio_encoding(self, encoding: str) -> Any:
        """Return the concrete enum/int value expected by Google SDK."""
        normalized = encoding.upper()
        enum_cls = self._audio_encoding_enum

        if enum_cls is not None:
            value_method = getattr(enum_cls, "Value", None)
            if callable(value_method):
                try:
                    return value_method(normalized)
                except (ValueError, KeyError):
                    pass
            for attr in (normalized, f"AUDIO_ENCODING_{normalized}"):
                if hasattr(enum_cls, attr):
                    return getattr(enum_cls, attr)

        audio_config_cls = self._audio_config_cls
        if audio_config_cls is not None:
            for attr in (normalized, f"AUDIO_ENCODING_{normalized}", "MP3", "AUDIO_ENCODING_MP3"):
                if hasattr(audio_config_cls, attr):
                    if attr not in (normalized, f"AUDIO_ENCODING_{normalized}"):
                        logger.warning("Unsupported audio encoding %s, defaulting to MP3", normalized)
                    return getattr(audio_config_cls, attr)

        logger.warning("Unsupported audio encoding %s, returning raw value", normalized)
        return normalized

    @staticmethod
    def _resolve_mime_type(encoding: str) -> str:
        mapping = {
            "MP3": "audio/mpeg",
            "OGG_OPUS": "audio/ogg",
            "LINEAR16": "audio/wav",
            "MULAW": "audio/basic",
            "ALAW": "audio/basic",
        }
        return mapping.get(encoding.upper(), "audio/mpeg")
