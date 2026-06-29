"""Tests for v0.1.2 TUI dashboard layout and IPC wiring."""

from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from textual.widgets import Static

from sybl.tui.app import IpcEventMessage, SyblTuiApp
from sybl.tui.screens.settings import SettingsScreen
from sybl.tui.widgets.chrome_bar import ChromeBar
from sybl.tui.widgets.context_strip import ContextStrip
from sybl.tui.widgets.hero_band import HeroBand
from sybl.tui.widgets.live_band import LiveBand
from sybl.tui.widgets.log_band import LogBand
from sybl.tui.widgets.session_pane import SessionPane
from sybl.tui.widgets.transcript_list import TranscriptList


async def _empty_event_stream():
    if False:  # pragma: no cover
        yield {}


def _mock_ipc() -> AsyncMock:
    ipc = AsyncMock()
    ipc.get_status.return_value = {
        "state": "idle",
        "provider": "deepgram",
        "hotkey_binding": "ctrl+alt+space",
        "hotkey_mode": "both",
        "audio_device": "default",
        "version": "0.1.2",
        "uptime_seconds": 42,
    }
    ipc.get_config.return_value = {
        "ui": {"onboarding_complete": True},
        "provider": {"preferred": "deepgram"},
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
    ipc.get_logs.return_value = {
        "entries": [
            {
                "timestamp": "2026-06-29T14:02:11",
                "level": "INFO",
                "message": "daemon ready",
            }
        ],
        "cursor": 1,
    }
    ipc.get_history.return_value = [
        {
            "final_text": "hello world",
            "provider": "deepgram",
            "audio_duration_seconds": 1.2,
            "latency_seconds": 0.4,
        }
    ]
    ipc.list_provider_keys.return_value = ["deepgram"]
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
async def test_dashboard_zone_widgets_exist() -> None:
    app = SyblTuiApp()
    app.ipc = _mock_ipc()
    stack = _tui_test_patches(app)
    with stack:
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.get_screen("dashboard")
            assert screen.query_one("#chrome-bar", ChromeBar)
            assert screen.query_one("#context-strip", ContextStrip)
            assert screen.query_one("#hero-band", HeroBand)
            assert screen.query_one("#session-pane", SessionPane)
            assert screen.query_one("#transcript-list", TranscriptList)
            assert screen.query_one("#log-band", LogBand)
            assert screen.query_one("#live-band", LiveBand)


@pytest.mark.asyncio
async def test_demo_mode_runs_without_daemon() -> None:
    app = SyblTuiApp(demo=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.get_screen("dashboard")
        assert screen.query_one("#hero-band", HeroBand)
        # The demo client seeds at least one transcript via get_history().
        transcripts = screen.query_one("#transcript-list", TranscriptList)
        assert len(transcripts.entries) >= 1


@pytest.mark.asyncio
async def test_dashboard_status_populates_zones() -> None:
    app = SyblTuiApp()
    app.ipc = _mock_ipc()
    stack = _tui_test_patches(app)
    with stack:
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.get_screen("dashboard")
            chrome = screen.query_one("#chrome-bar", ChromeBar)
            context = screen.query_one("#context-strip", ContextStrip)
            hero = screen.query_one("#hero-band", HeroBand)
            assert "live" in str(chrome.query_one("#daemon-chip", Static).render())
            assert "deepgram" in str(context.render())
            assert "IDLE" in str(hero.query_one("#hero-state", Static).render())


@pytest.mark.asyncio
async def test_edit_config_reloads_daemon() -> None:
    app = SyblTuiApp()
    ipc = _mock_ipc()
    app.ipc = ipc
    stack = _tui_test_patches(app)
    with stack:
        async with app.run_test() as pilot:
            await pilot.pause()
            screen = app.get_screen("dashboard")
            await screen._reload_after_edit(Path("config.toml"))
            ipc.patch_config.assert_awaited()
            payload = ipc.patch_config.await_args.args[0]
            assert "provider" in payload
            assert "hotkey" in payload


@pytest.mark.asyncio
async def test_edit_config_demo_skips_daemon() -> None:
    app = SyblTuiApp(demo=True)
    async with app.run_test() as pilot:
        await pilot.pause()
        screen = app.get_screen("dashboard")
        app.ipc.patch_config = AsyncMock()
        await screen._reload_after_edit(Path("config.toml"))
        app.ipc.patch_config.assert_not_awaited()


def _tui_test_patches(app: SyblTuiApp) -> ExitStack:
    stack = ExitStack()
    stack.enter_context(patch.object(app, "_maybe_show_onboarding", new=AsyncMock()))
    stack.enter_context(patch.object(app, "run_worker"))
    return stack


@pytest.mark.asyncio
async def test_level_event_updates_meter() -> None:
    app = SyblTuiApp()
    app.ipc = _mock_ipc()
    stack = _tui_test_patches(app)
    with stack:
        async with app.run_test() as pilot:
            await pilot.pause()
            app.on_ipc_event_message(IpcEventMessage({"type": "level", "value": 0.75}))
            await pilot.pause()
            hero = app.get_screen("dashboard").query_one("#hero-band", HeroBand)
            assert abs(hero.meter_value - 0.75) < 1e-6


@pytest.mark.asyncio
async def test_settings_nav_switches_section() -> None:
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
            nav = settings.query_one("#settings-nav-list")
            switcher = settings.query_one("#settings-content")
            nav.index = 1
            nav.action_select_cursor()
            await pilot.pause()
            assert switcher.current == "hotkey"


@pytest.mark.asyncio
async def test_settings_hotkey_save_calls_patch_config() -> None:
    app = SyblTuiApp()
    ipc = _mock_ipc()
    app.ipc = ipc
    stack = _tui_test_patches(app)
    with stack:
        async with app.run_test() as pilot:
            await pilot.pause()
            await app.push_screen(SettingsScreen())
            await pilot.pause()
            settings = app.screen_stack[-1]
            assert isinstance(settings, SettingsScreen)
            await settings._save_hotkey()
            ipc.patch_config.assert_awaited()
            call_args = ipc.patch_config.await_args
            assert call_args is not None
            patch_payload = call_args.args[0]
            assert patch_payload["hotkey"]["binding"] == "ctrl+alt+space"
            assert patch_payload["hotkey"]["ptt_hold_ms"] == 200
