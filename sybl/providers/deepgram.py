"""Deepgram streaming and batch STT provider."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterable

from deepgram import AsyncDeepgramClient, DeepgramClient
from deepgram.core.api_error import ApiError
from deepgram.listen.v1.types import ListenV1Results
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from sybl.audio.types import TARGET_SAMPLE_RATE
from sybl.config.models import DeepgramConfig
from sybl.config.vocabulary import format_deepgram_keyterms
from sybl.providers.errors import (
    STTAuthError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)
from sybl.providers.pcm import pcm_to_wav_bytes
from sybl.providers.types import TranscriptionResult
from sybl.secrets.store import get_provider_key

logger = logging.getLogger("sybl.providers.deepgram")


class DeepgramProvider:
    name = "deepgram"

    def __init__(
        self,
        config: DeepgramConfig,
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
            text = await self._transcribe_batch(audio)
            yield TranscriptionResult(text=text, is_final=True)
            return

        async for result in self._transcribe_stream(audio):
            yield result

    async def _transcribe_batch(self, pcm: bytes) -> str:
        if not pcm:
            raise STTProviderError("No audio data to transcribe")

        wav_bytes = pcm_to_wav_bytes(pcm)
        api_key = self._resolve_api_key()
        return await asyncio.to_thread(
            self._transcribe_file_with_retry,
            api_key,
            wav_bytes,
        )

    async def _transcribe_stream(
        self,
        audio: AsyncIterable[bytes],
    ) -> AsyncGenerator[TranscriptionResult, None]:
        api_key = self._resolve_api_key()
        client = AsyncDeepgramClient(api_key=api_key)
        connect_kwargs = self._connect_kwargs()

        try:
            async with client.listen.v1.connect(**connect_kwargs) as socket:
                results_queue: asyncio.Queue[TranscriptionResult | None] = (
                    asyncio.Queue()
                )

                async def receiver() -> None:
                    try:
                        while True:
                            message = await socket.recv()
                            if isinstance(message, ListenV1Results):
                                parsed = _result_from_listen(message)
                                if parsed.text:
                                    await results_queue.put(parsed)
                    except Exception as exc:
                        logger.debug("Deepgram receiver ended: %s", exc)
                    finally:
                        await results_queue.put(None)

                receiver_task = asyncio.create_task(receiver())
                try:
                    async for chunk in audio:
                        if chunk:
                            await socket.send_media(chunk)

                    await socket.send_close_stream()

                    while True:
                        item = await results_queue.get()
                        if item is None:
                            break
                        yield item
                finally:
                    receiver_task.cancel()
                    try:
                        await receiver_task
                    except asyncio.CancelledError:
                        pass
        except ApiError as exc:
            raise _map_api_error(exc) from exc
        except Exception as exc:
            raise STTProviderError(f"Deepgram streaming failed: {exc}") from exc

    def _transcribe_file_with_retry(self, api_key: str, wav_bytes: bytes) -> str:
        @retry(
            retry=retry_if_exception_type((STTRateLimitError, STTTimeoutError)),
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            reraise=True,
        )
        def _attempt() -> str:
            return self._transcribe_file_once(api_key, wav_bytes)

        return _attempt()

    def _transcribe_file_once(self, api_key: str, wav_bytes: bytes) -> str:
        kwargs = self._media_kwargs()
        try:
            client = DeepgramClient(api_key=api_key)
            response = client.listen.v1.media.transcribe_file(
                request=wav_bytes,
                **kwargs,
            )
        except ApiError as exc:
            raise _map_api_error(exc) from exc
        except Exception as exc:
            raise STTProviderError(f"Deepgram transcription failed: {exc}") from exc

        try:
            return response.results.channels[0].alternatives[0].transcript
        except (AttributeError, IndexError) as exc:
            raise STTProviderError("Deepgram returned no transcript text") from exc

    def _connect_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "model": self._config.model,
            "encoding": "linear16",
            "sample_rate": str(TARGET_SAMPLE_RATE),
            "channels": "1",
            "interim_results": "true" if self._config.interim_results else "false",
            "punctuate": "true" if self._config.punctuate else "false",
            "smart_format": "true" if self._config.smart_format else "false",
        }
        if self._config.language is not None:
            kwargs["language"] = self._config.language
        kwargs.update(self._vocabulary_kwargs())
        return kwargs

    def _media_kwargs(self) -> dict[str, object]:
        kwargs: dict[str, object] = {
            "model": self._config.model,
            "punctuate": self._config.punctuate,
            "smart_format": self._config.smart_format,
        }
        if self._config.language is not None:
            kwargs["language"] = self._config.language
        kwargs.update(self._vocabulary_kwargs())
        return kwargs

    def _vocabulary_kwargs(self) -> dict[str, object]:
        if not self._vocabulary:
            return {}
        return {"keyterm": format_deepgram_keyterms(self._vocabulary)}

    def _resolve_api_key(self) -> str:
        if self._api_key:
            return self._api_key
        key = get_provider_key("deepgram")
        if not key:
            raise STTAuthError(
                "Deepgram API key not found. Run: sybl config set-key deepgram"
            )
        return key


def _result_from_listen(message: ListenV1Results) -> TranscriptionResult:
    alternative = message.channel.alternatives[0]
    return TranscriptionResult(
        text=alternative.transcript,
        is_final=bool(message.is_final),
        confidence=alternative.confidence,
    )


def _map_api_error(exc: ApiError) -> STTProviderError:
    status = exc.status_code
    if status == 401:
        return STTAuthError("Deepgram authentication failed")
    if status == 429:
        return STTRateLimitError("Deepgram rate limit exceeded")
    if status is not None and status >= 500:
        return STTTimeoutError(f"Deepgram server error ({status})")
    return STTProviderError(f"Deepgram API error ({status}): {exc.body}")
