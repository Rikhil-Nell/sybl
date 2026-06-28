"""Groq Whisper batch STT provider."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterable

from groq import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    Groq,
    RateLimitError,
)
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from navi.config.models import GroqConfig
from navi.config.vocabulary import build_groq_vocabulary_prompt
from navi.providers.errors import (
    STTAuthError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)
from navi.providers.pcm import pcm_to_wav_bytes
from navi.providers.types import TranscriptionResult
from navi.secrets.store import get_provider_key

logger = logging.getLogger("navi.providers.groq")


class GroqProvider:
    name = "groq"

    def __init__(
        self,
        config: GroqConfig,
        *,
        api_key: str | None = None,
        vocabulary: list[str] | None = None,
    ) -> None:
        self._config = config
        self._api_key = api_key
        self._vocabulary = list(vocabulary or [])

    async def transcribe(
        self,
        audio: bytes | AsyncIterable[bytes],
    ) -> AsyncGenerator[TranscriptionResult, None]:
        if isinstance(audio, bytes):
            pcm = audio
        else:
            pcm = await self._buffer_stream(audio)

        if not pcm:
            raise STTProviderError("No audio data to transcribe")

        wav_bytes = pcm_to_wav_bytes(pcm)
        text = await self._transcribe_wav(wav_bytes)
        yield TranscriptionResult(text=text, is_final=True)

    async def _buffer_stream(self, audio: AsyncIterable[bytes]) -> bytes:
        chunks: list[bytes] = []
        async for chunk in audio:
            chunks.append(chunk)
        return b"".join(chunks)

    async def _transcribe_wav(self, wav_bytes: bytes) -> str:
        api_key = self._resolve_api_key()
        return await asyncio.to_thread(self._call_groq_with_retry, api_key, wav_bytes)

    def _resolve_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        key = get_provider_key("groq")
        if not key:
            raise STTAuthError(
                "Groq API key not found. Run: navi config set-key groq"
            )
        return key

    def _call_groq_with_retry(self, api_key: str, wav_bytes: bytes) -> str:
        @retry(
            retry=retry_if_exception_type((STTRateLimitError, STTTimeoutError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            reraise=True,
        )
        def _attempt() -> str:
            return self._call_groq_once(api_key, wav_bytes)

        return _attempt()

    def _call_groq_once(self, api_key: str, wav_bytes: bytes) -> str:
        kwargs: dict[str, object] = {
            "file": ("audio.wav", wav_bytes),
            "model": self._config.model,
            "response_format": "json",
            "temperature": self._config.temperature,
        }
        if self._config.language is not None:
            kwargs["language"] = self._config.language
        prompt = self._effective_prompt()
        if prompt is not None:
            kwargs["prompt"] = prompt

        try:
            client = Groq(api_key=api_key)
            result = client.audio.transcriptions.create(**kwargs)
        except AuthenticationError as exc:
            raise STTAuthError("Groq authentication failed") from exc
        except RateLimitError as exc:
            raise STTRateLimitError("Groq rate limit exceeded") from exc
        except APIConnectionError as exc:
            raise STTTimeoutError("Groq connection failed") from exc
        except APIStatusError as exc:
            if exc.status_code >= 500:
                raise STTTimeoutError(f"Groq server error ({exc.status_code})") from exc
            raise STTProviderError(
                f"Groq API error ({exc.status_code}): {exc}"
            ) from exc
        except Exception as exc:
            raise STTProviderError(f"Groq transcription failed: {exc}") from exc

        text = getattr(result, "text", None)
        if text is None:
            raise STTProviderError("Groq returned no transcript text")
        return str(text)

    def _effective_prompt(self) -> str | None:
        if self._config.prompt is not None:
            return self._config.prompt
        if not self._vocabulary:
            return None
        return build_groq_vocabulary_prompt(self._vocabulary)
