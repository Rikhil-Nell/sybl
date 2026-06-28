"""Tests for core state machine and transcribe pipeline."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from navi.config.models import NaviConfig
from navi.core.state import InvalidTransitionError, SessionState, StateMachine
from navi.core.transcribe import transcribe_pcm
from navi.providers.errors import STTProviderError
from navi.providers.types import TranscriptionResult


def test_state_machine_starts_idle() -> None:
    machine = StateMachine()
    assert machine.state is SessionState.IDLE


def test_state_machine_valid_transitions() -> None:
    machine = StateMachine()
    machine.transition(SessionState.LISTENING)
    machine.transition(SessionState.PROCESSING)
    machine.transition(SessionState.IDLE)
    assert machine.state is SessionState.IDLE


def test_state_machine_invalid_transition_raises() -> None:
    machine = StateMachine()
    with pytest.raises(InvalidTransitionError):
        machine.transition(SessionState.PROCESSING)


def test_state_machine_reset() -> None:
    machine = StateMachine()
    machine.transition(SessionState.LISTENING)
    machine.reset()
    assert machine.state is SessionState.IDLE


@pytest.mark.asyncio
async def test_transcribe_pcm_collects_final_text() -> None:
    config = NaviConfig()
    pcm = b"\x00\x01" * 1600

    async def fake_transcribe(_audio):
        yield TranscriptionResult(text="hello", is_final=True)

    mock_provider = AsyncMock()
    mock_provider.transcribe = fake_transcribe
    mock_provider.name = "groq"

    with patch(
        "navi.core.transcribe.resolve_provider",
        return_value=("groq", mock_provider),
    ):
        outcome = await transcribe_pcm(
            config,
            pcm,
            audio_duration_seconds=1.0,
            peak_dbfs=-20.0,
        )

    assert outcome.text == "hello"
    assert outcome.provider == "groq"
    assert outcome.model == "whisper-large-v3-turbo"
    assert outcome.audio_duration_seconds == 1.0
    assert outcome.peak_dbfs == -20.0
    assert outcome.latency_seconds >= 0.0


@pytest.mark.asyncio
async def test_transcribe_pcm_propagates_stt_errors() -> None:
    config = NaviConfig()
    pcm = b"\x00\x01" * 1600

    async def failing_transcribe(_audio):
        raise STTProviderError("boom")
        yield  # pragma: no cover

    mock_provider = AsyncMock()
    mock_provider.transcribe = failing_transcribe
    mock_provider.name = "groq"

    with patch(
        "navi.core.transcribe.resolve_provider",
        return_value=("groq", mock_provider),
    ):
        with pytest.raises(STTProviderError, match="boom"):
            await transcribe_pcm(config, pcm)


@pytest.mark.asyncio
async def test_collect_stream_text_accumulates_final_segments() -> None:
    from navi.core.transcribe import _collect_stream_text

    async def results():
        yield TranscriptionResult(text="Hello.", is_final=True)
        yield TranscriptionResult(text="How are", is_final=False)
        yield TranscriptionResult(text="How are you?", is_final=True)

    text = await _collect_stream_text(results())
    assert text == "Hello. How are you?"


@pytest.mark.asyncio
async def test_collect_stream_text_uses_trailing_interim_when_no_final() -> None:
    from navi.core.transcribe import _collect_stream_text

    async def results():
        yield TranscriptionResult(text="hel", is_final=False)
        yield TranscriptionResult(text="hello world", is_final=False)

    text = await _collect_stream_text(results())
    assert text == "hello world"


@pytest.mark.asyncio
async def test_collect_stream_text_prefers_committed_over_last_interim() -> None:
    from navi.core.transcribe import _collect_stream_text

    async def results():
        yield TranscriptionResult(text="first part", is_final=True)
        yield TranscriptionResult(text="second part", is_final=False)

    text = await _collect_stream_text(results())
    assert text == "first part second part"
