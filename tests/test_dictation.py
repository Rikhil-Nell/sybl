"""Tests for dictation controller orchestration."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from navi.config.models import HotkeyConfig, NaviConfig
from navi.core.dictation import DictationController
from navi.core.state import SessionState
from navi.core.transcribe import TranscribeOutcome
from navi.hotkeys.base import HotkeyEvent
from navi.hotkeys.focus import FocusTarget


@pytest.fixture
def navi_config() -> NaviConfig:
    return NaviConfig(
        hotkey=HotkeyConfig(min_duration_ms=250, streaming="off"),
    )


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
    navi_config: NaviConfig,
) -> None:
    controller = DictationController(navi_config)
    mock_session = _mock_session(duration_seconds=1.0)
    focus = FocusTarget(hwnd=123, pid=456, title="Notepad")

    with (
        patch("navi.core.dictation.capture_foreground", return_value=focus),
        patch(
            "navi.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("navi.core.dictation.AudioCaptureSession", return_value=mock_session),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)

    assert controller.state is SessionState.LISTENING
    assert controller.focus_target == focus
    mock_session.start.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_transcribes_and_returns_idle(navi_config: NaviConfig) -> None:
    controller = DictationController(navi_config)
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
        patch("navi.core.dictation.capture_foreground", return_value=FocusTarget()),
        patch(
            "navi.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("navi.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch(
            "navi.core.dictation.transcribe_pcm",
            AsyncMock(return_value=outcome),
        ) as mock_transcribe,
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE)

    assert controller.state is SessionState.IDLE
    mock_transcribe.assert_awaited_once()


@pytest.mark.asyncio
async def test_short_capture_skips_stt(navi_config: NaviConfig) -> None:
    controller = DictationController(navi_config)
    mock_session = _mock_session(duration_seconds=0.05)

    with (
        patch("navi.core.dictation.capture_foreground", return_value=FocusTarget()),
        patch(
            "navi.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("navi.core.dictation.AudioCaptureSession", return_value=mock_session),
        patch("navi.core.dictation.transcribe_pcm", AsyncMock()) as mock_transcribe,
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.DEACTIVATE)

    assert controller.state is SessionState.IDLE
    mock_transcribe.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_discards_capture(navi_config: NaviConfig) -> None:
    controller = DictationController(navi_config)
    mock_session = _mock_session(duration_seconds=1.0)

    with (
        patch("navi.core.dictation.capture_foreground", return_value=FocusTarget()),
        patch(
            "navi.core.dictation.resolve_provider",
            return_value=("groq", MagicMock()),
        ),
        patch("navi.core.dictation.AudioCaptureSession", return_value=mock_session),
    ):
        await controller.handle_hotkey_event(HotkeyEvent.ACTIVATE)
        await controller.handle_hotkey_event(HotkeyEvent.CANCEL)

    assert controller.state is SessionState.IDLE
    mock_session.cancel.assert_awaited_once()
