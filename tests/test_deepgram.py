"""Tests for Deepgram provider parsing and error mapping."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from deepgram.core.api_error import ApiError
from deepgram.listen.v1.types import (
    ListenV1Results,
    ListenV1ResultsChannel,
    ListenV1ResultsChannelAlternativesItem,
    ListenV1ResultsMetadata,
    ListenV1ResultsMetadataModelInfo,
)

from sybl.config.models import DeepgramConfig
from sybl.providers.deepgram import (
    DeepgramProvider,
    _map_api_error,
    _result_from_listen,
)
from sybl.providers.errors import STTAuthError, STTProviderError, STTRateLimitError


def _sample_results(*, is_final: bool, transcript: str) -> ListenV1Results:
    return ListenV1Results(
        channel_index=[0],
        duration=1.0,
        start=0.0,
        is_final=is_final,
        channel=ListenV1ResultsChannel(
            alternatives=[
                ListenV1ResultsChannelAlternativesItem(
                    transcript=transcript,
                    confidence=0.95,
                    words=[],
                )
            ]
        ),
        metadata=ListenV1ResultsMetadata(
            request_id="req",
            model_info=ListenV1ResultsMetadataModelInfo(
                name="nova-3",
                version="1",
                arch="nova-3",
            ),
            model_uuid="uuid",
        ),
    )


def test_result_from_listen_partial() -> None:
    result = _result_from_listen(_sample_results(is_final=False, transcript="hello"))
    assert result.text == "hello"
    assert result.is_final is False
    assert result.confidence == 0.95


def test_result_from_listen_final() -> None:
    result = _result_from_listen(
        _sample_results(is_final=True, transcript="hello world")
    )
    assert result.is_final is True


@pytest.mark.asyncio
async def test_deepgram_batch_yields_single_final_result() -> None:
    provider = DeepgramProvider(DeepgramConfig(), api_key="test-key")
    pcm = b"\x00\x01" * 1600

    with patch.object(
        DeepgramProvider,
        "_transcribe_batch",
        return_value="batch transcript",
    ):
        results = [item async for item in provider.transcribe(pcm)]

    assert len(results) == 1
    assert results[0].text == "batch transcript"
    assert results[0].is_final is True


@pytest.mark.asyncio
async def test_deepgram_streaming_yields_partial_and_final() -> None:
    provider = DeepgramProvider(DeepgramConfig(), api_key="test-key")

    async def fake_stream(_self, _audio):
        yield _result_from_listen(_sample_results(is_final=False, transcript="hel"))
        yield _result_from_listen(_sample_results(is_final=True, transcript="hello"))

    async def chunks():
        yield b"\x00\x01" * 800

    with patch.object(DeepgramProvider, "_transcribe_stream", fake_stream):
        results = [item async for item in provider.transcribe(chunks())]

    assert len(results) == 2
    assert results[0].is_final is False
    assert results[1].is_final is True


def test_map_api_error_auth() -> None:
    exc = ApiError(status_code=401, body="bad key")
    assert isinstance(_map_api_error(exc), STTAuthError)


def test_map_api_error_rate_limit() -> None:
    exc = ApiError(status_code=429, body="slow down")
    assert isinstance(_map_api_error(exc), STTRateLimitError)


def test_deepgram_batch_api_error() -> None:
    provider = DeepgramProvider(DeepgramConfig(), api_key="test-key")
    exc = ApiError(status_code=400, body="bad request")
    with patch("sybl.providers.deepgram.DeepgramClient") as mock_client:
        mock_client.return_value.listen.v1.media.transcribe_file.side_effect = exc
        with pytest.raises(STTProviderError, match="Deepgram API error"):
            provider._transcribe_file_once("test-key", b"RIFFfake")
