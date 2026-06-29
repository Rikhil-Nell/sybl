"""Tests for TUI settings hotkey validation and section navigation."""

from __future__ import annotations

from contextlib import ExitStack
from unittest.mock import AsyncMock, patch

import pytest

from sybl.hotkeys.bindings import BindingParseError, parse_binding
from sybl.tui.app import SyblTuiApp
from sybl.tui.screens.settings import _SECTIONS, SettingsScreen


def test_settings_hotkey_bindings_validate() -> None:
    parse_binding("ctrl+alt+space")
    parse_binding("esc")


def test_settings_hotkey_bindings_reject_invalid() -> None:
    with pytest.raises(BindingParseError):
        parse_binding("!!!")


async def _empty_event_stream():
    if False:  # pragma: no cover
        yield {}


def _mock_ipc() -> AsyncMock:
    ipc = AsyncMock()
    ipc.get_status.return_value = {"state": "idle", "provider": "groq"}
    ipc.get_logs.return_value = {"entries": [], "cursor": 0}
    ipc.get_history.return_value = []
    ipc.get_config.return_value = {
        "provider": {"preferred": "groq"},
        "hotkey": {
            "mode": "both",
            "binding": "ctrl+alt+space",
            "cancel_binding": "esc",
            "toggle_double_press_ms": 400,
            "ptt_hold_ms": 200,
            "streaming": "auto",
            "min_duration_ms": 250,
        },
    }
    ipc.list_sounds.return_value = {
        "sounds_dir": "/tmp/sounds",
        "files": [],
        "start_file": None,
        "stop_file": None,
    }
    ipc.connect = AsyncMock()

    async def _stream():
        async for item in _empty_event_stream():
            yield item

    ipc.stream_events = _stream
    return ipc


@pytest.mark.asyncio
async def test_settings_section_ids_match_nav() -> None:
    assert [key for key, _ in _SECTIONS] == [
        "provider",
        "hotkey",
        "audio",
        "indicator",
        "injection",
        "text",
        "advanced",
    ]


def _tui_test_patches(app: SyblTuiApp) -> ExitStack:
    stack = ExitStack()
    stack.enter_context(patch.object(app, "_maybe_show_onboarding", new=AsyncMock()))
    stack.enter_context(patch.object(app, "run_worker"))
    return stack


@pytest.mark.asyncio
async def test_settings_hotkey_rejects_invalid_binding() -> None:
    app = SyblTuiApp()
    app.ipc = _mock_ipc()
    stack = _tui_test_patches(app)
    with stack:
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(SettingsScreen())
            await pilot.pause()
            settings = app.screen_stack[-1]
            assert isinstance(settings, SettingsScreen)
            from textual.widgets import Input

            settings.query_one("#settings-content").current = "hotkey"
            await pilot.pause()
            settings.query_one("#hotkey-binding", Input).value = "!!!"
            await settings._save_hotkey()
            status = str(settings.query_one("#settings-status").render())
            assert "Invalid binding" in status


@pytest.mark.asyncio
async def test_settings_hotkey_rejects_bad_ptt_hold() -> None:
    app = SyblTuiApp()
    app.ipc = _mock_ipc()
    stack = _tui_test_patches(app)
    with stack:
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(SettingsScreen())
            await pilot.pause()
            settings = app.screen_stack[-1]
            assert isinstance(settings, SettingsScreen)
            from textual.widgets import Input

            settings.query_one("#settings-content").current = "hotkey"
            await pilot.pause()
            settings.query_one("#hotkey-ptt-hold-ms", Input).value = "50"
            await settings._save_hotkey()
            status = str(settings.query_one("#settings-status").render())
            assert "PTT hold" in status
