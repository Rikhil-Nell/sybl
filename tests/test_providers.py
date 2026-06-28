"""Tests for STT provider abstraction and Groq integration."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from groq import APIConnectionError, APIStatusError, AuthenticationError, RateLimitError

from sybl.config.models import GroqConfig, SyblConfig
from sybl.providers.errors import (
    STTAuthError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)
from sybl.providers.groq import GroqProvider
from sybl.providers.pcm import pcm_to_wav_bytes
from sybl.providers.registry import get_provider, list_providers
from sybl.providers.types import TranscriptionResult


def test_transcription_result_defaults() -> None:
    result = TranscriptionResult(text="hello", is_final=True)
    assert result.confidence is None


def test_pcm_to_wav_bytes_has_wav_header() -> None:
    pcm = b"\x00\x01" * 160
    wav = pcm_to_wav_bytes(pcm)
    assert wav.startswith(b"RIFF")
    assert b"WAVE" in wav[:16]


def test_list_providers_includes_groq_and_deepgram() -> None:
    providers = list_providers()
    assert "groq" in providers
    assert "deepgram" in providers


def test_get_provider_unknown_raises() -> None:
    config = SyblConfig()
    with pytest.raises(STTProviderError, match="Unknown STT provider"):
        get_provider("unknown", config)


def test_get_provider_returns_groq() -> None:
    config = SyblConfig()
    provider = get_provider("groq", config)
    assert provider.name == "groq"


@pytest.mark.asyncio
async def test_groq_batch_transcribe_yields_single_final_result() -> None:
    provider = GroqProvider(GroqConfig(), api_key="test-key")
    pcm = b"\x00\x01" * 1600

    with patch.object(GroqProvider, "_transcribe_wav", return_value="hello world"):
        results = [item async for item in provider.transcribe(pcm)]

    assert len(results) == 1
    assert results[0].text == "hello world"
    assert results[0].is_final is True


@pytest.mark.asyncio
async def test_groq_empty_pcm_raises() -> None:
    provider = GroqProvider(GroqConfig(), api_key="test-key")
    with pytest.raises(STTProviderError, match="No audio data"):
        [item async for item in provider.transcribe(b"")]


@pytest.mark.asyncio
async def test_groq_streaming_buffers_chunks() -> None:
    provider = GroqProvider(GroqConfig(), api_key="test-key")

    async def chunks():
        yield b"\x00\x01" * 800
        yield b"\x00\x02" * 800

    with patch.object(GroqProvider, "_transcribe_wav", return_value="streamed") as mock:
        results = [item async for item in provider.transcribe(chunks())]

    assert results[0].text == "streamed"
    uploaded = mock.call_args[0][0]
    assert uploaded.startswith(b"RIFF")


@pytest.mark.asyncio
async def test_groq_missing_api_key_raises_auth_error() -> None:
    provider = GroqProvider(GroqConfig(), api_key=None)
    with patch("sybl.providers.groq.get_provider_key", return_value=None):
        with pytest.raises(STTAuthError, match="API key not found"):
            await provider._transcribe_wav(b"RIFFfake")


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (AuthenticationError("bad key", response=MagicMock(), body=None), STTAuthError),
        (
            RateLimitError("slow down", response=MagicMock(), body=None),
            STTRateLimitError,
        ),
        (APIConnectionError(request=MagicMock()), STTTimeoutError),
    ],
)
def test_groq_error_mapping(exc: Exception, expected: type[Exception]) -> None:
    provider = GroqProvider(GroqConfig(), api_key="test-key")
    with patch("sybl.providers.groq.Groq") as mock_groq:
        mock_groq.return_value.audio.transcriptions.create.side_effect = exc
        with pytest.raises(expected):
            provider._call_groq_once("test-key", b"RIFFfake")


def test_groq_5xx_maps_to_timeout() -> None:
    provider = GroqProvider(GroqConfig(), api_key="test-key")
    response = MagicMock()
    response.status_code = 503
    exc = APIStatusError("server error", response=response, body=None)
    with patch("sybl.providers.groq.Groq") as mock_groq:
        mock_groq.return_value.audio.transcriptions.create.side_effect = exc
        with pytest.raises(STTTimeoutError, match="server error"):
            provider._call_groq_once("test-key", b"RIFFfake")


def test_groq_4xx_maps_to_provider_error() -> None:
    provider = GroqProvider(GroqConfig(), api_key="test-key")
    response = MagicMock()
    response.status_code = 400
    exc = APIStatusError("bad request", response=response, body=None)
    with patch("sybl.providers.groq.Groq") as mock_groq:
        mock_groq.return_value.audio.transcriptions.create.side_effect = exc
        with pytest.raises(STTProviderError, match="Groq API error"):
            provider._call_groq_once("test-key", b"RIFFfake")
