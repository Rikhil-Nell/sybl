"""Tests for dictation controller orchestration."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sybl.config.models import HotkeyConfig, InjectConfig, SyblConfig
from sybl.core.dictation import DictationController
from sybl.core.state import SessionState
from sybl.core.transcribe import TranscribeOutcome
from sybl.hotkeys.base import HotkeyEvent
from sybl.hotkeys.focus import FocusTarget
from sybl.inject.base import InjectError


@pytest.fixture
def sybl_config() -> SyblConfig:
    return SyblConfig(
        hotkey=HotkeyConfig(min_duration_ms=250, streaming="off"),
        inject=InjectConfig(enabled=True),
    )


@pytest.fixture
def mock_injector() -> AsyncMock:
    return AsyncMock()


def _mock_session(*, duration_seconds: float) -> MagicMock:
    session = MagicMock()
    session.start = AsyncMock()
    session.stop = AsyncMock(return_value=b"pcm")
    session.cancel = AsyncMock()
    session.stats.return_value = MagicMock(
        duration_seconds=duration_seconds,
        peak_dbfs=-10.0,
    )
    return session


@pytest.mark.asyncio
async def test_activate_captures_focus_and_starts_listening(
    sybl_config: SyblConfig,
    mock_injector: AsyncMock,
) -> None:
    controller = DictationController(sybl_config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=1.0)
    focus = FocusTarget(hwnd=123, pid=456, title="Notepad")

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=focus),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)

    assert controller.state is SessionState.LISTENING
    assert controller.focus_target == focus
    mock_session.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_applies_postprocess_before_inject(
    sybl_config: SyblConfig,
    mock_injector: AsyncMock,
) -> None:
    controller = DictationController(sybl_config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=1.0)
    focus = FocusTarget(hwnd=123, pid=456, title="Notepad")
    outcome = TranscribeOutcome(
        text="um uh hello world",
        provider="groq",
        model="whisper-large-v3-turbo",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
        peak_dbfs=-10.0,
    )

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=focus),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch(
            "sybl.core.dictation.transcribe_pcm",
            AsyncMock(return_value=outcome),
        ),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE)

    mock_injector.inject.assert_awaited_once_with("Hello world", focus)


@pytest.mark.asyncio
async def test_deactivate_awaits_running_stream_task(
    mock_injector: AsyncMock,
) -> None:
    config = SyblConfig(
        hotkey=HotkeyConfig(min_duration_ms=250, streaming="on"),
        inject=InjectConfig(enabled=True),
    )
    controller = DictationController(config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=1.0)
    focus = FocusTarget(hwnd=123, pid=456, title="Notepad")
    outcome = TranscribeOutcome(
        text="hello world",
        provider="deepgram",
        model="nova-3",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
        peak_dbfs=-10.0,
    )
    release_stream = asyncio.Event()

    async def slow_stream(*_args, **_kwargs):
        await release_stream.wait()
        return outcome

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=focus),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("deepgram", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch(
            "sybl.core.dictation.transcribe_stream",
            side_effect=slow_stream,
        ),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        assert controller._stream_task is not None
        assert not controller._stream_task.done()

        deactivate_task = asyncio.create_task(
            controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE),
        )
        await asyncio.sleep(0)
        release_stream.set()
        await deactivate_task

    assert controller.state is SessionState.IDLE
    mock_injector.inject.assert_awaited_once_with("Hello world", focus)


@pytest.mark.asyncio
async def test_deactivate_injects_transcript_and_returns_idle(
    sybl_config: SyblConfig,
    mock_injector: AsyncMock,
) -> None:
    controller = DictationController(sybl_config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=1.0)
    focus = FocusTarget(hwnd=123, pid=456, title="Notepad")
    outcome = TranscribeOutcome(
        text="hello",
        provider="groq",
        model="whisper-large-v3-turbo",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
        peak_dbfs=-10.0,
    )

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=focus),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch(
            "sybl.core.dictation.transcribe_pcm",
            AsyncMock(return_value=outcome),
        ) as mock_transcribe,
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE)

    assert controller.state is SessionState.IDLE
    mock_transcribe.assert_awaited_once()
    mock_injector.inject.assert_awaited_once_with("Hello", focus)


@pytest.mark.asyncio
async def test_deactivate_skips_inject_when_disabled(
    mock_injector: AsyncMock,
) -> None:
    config = SyblConfig(
        hotkey=HotkeyConfig(min_duration_ms=250, streaming="off"),
        inject=InjectConfig(enabled=False),
    )
    controller = DictationController(config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=1.0)
    outcome = TranscribeOutcome(
        text="hello",
        provider="groq",
        model="whisper-large-v3-turbo",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
        peak_dbfs=-10.0,
    )

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=FocusTarget()),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch(
            "sybl.core.dictation.transcribe_pcm",
            AsyncMock(return_value=outcome),
        ),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE)

    mock_injector.inject.assert_not_called()


@pytest.mark.asyncio
async def test_inject_failure_moves_to_error_then_idle(
    sybl_config: SyblConfig,
    mock_injector: AsyncMock,
) -> None:
    mock_injector.inject.side_effect = InjectError("paste failed")
    controller = DictationController(sybl_config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=1.0)
    outcome = TranscribeOutcome(
        text="hello",
        provider="groq",
        model="whisper-large-v3-turbo",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
        peak_dbfs=-10.0,
    )

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=FocusTarget()),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch(
            "sybl.core.dictation.transcribe_pcm",
            AsyncMock(return_value=outcome),
        ),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE)

    assert controller.state is SessionState.IDLE
    mock_injector.inject.assert_awaited_once()


@pytest.mark.asyncio
async def test_short_capture_skips_stt(
    sybl_config: SyblConfig,
    mock_injector: AsyncMock,
) -> None:
    controller = DictationController(sybl_config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=0.05)

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=FocusTarget()),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch("sybl.core.dictation.transcribe_pcm", AsyncMock()) as mock_transcribe,
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE)

    assert controller.state is SessionState.IDLE
    mock_transcribe.assert_not_called()
    mock_injector.inject.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_discards_capture(
    sybl_config: SyblConfig,
    mock_injector: AsyncMock,
) -> None:
    controller = DictationController(sybl_config, injector=mock_injector)
    mock_session = _mock_session(duration_seconds=1.0)

    with (
        patch("sybl.core.dictation.capture_foreground", return_value=FocusTarget()),
        patch(
            "sybl.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("sybl.core.dictation.AudioCaptureSession", return_value=mock_session),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.CANCEL)

    assert controller.state is SessionState.IDLE
    mock_session.cancel.assert_awaited_once()
