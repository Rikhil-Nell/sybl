"""Textual TUI application."""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path

from textual.app import App, ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.worker import get_current_worker

from sybl.ipc.client import IpcConnectionError
from sybl.tui.client import TuiIpcClient
from sybl.tui.screens.dashboard import DashboardScreen
from sybl.tui.screens.help import HelpScreen
from sybl.tui.screens.onboarding import OnboardingScreen
from sybl.tui.widgets.chrome_bar import ChromeBar
from sybl.tui.widgets.context_strip import ContextStrip
from sybl.tui.widgets.hero_band import HeroBand
from sybl.tui.widgets.live_band import LiveBand
from sybl.tui.widgets.log_band import LogBand
from sybl.tui.widgets.session_pane import SessionPane
from sybl.tui.widgets.transcript_list import TranscriptList

logger = logging.getLogger("sybl.tui")


class IpcEventMessage(Message):
    def __init__(self, payload: dict) -> None:
        super().__init__()
        self.payload = payload


class DaemonConnectionMessage(Message):
    def __init__(self, connected: bool, detail: str = "") -> None:
        super().__init__()
        self.connected = connected
        self.detail = detail


class SyblTuiApp(App):
    TITLE = "sybl"
    CSS_PATH = Path(__file__).parent / "theme" / "sibyl_royal.tcss"

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("question_mark", "open_help", "Help"),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "onboarding": OnboardingScreen,
    }

    def __init__(self, *, demo: bool = False) -> None:
        super().__init__()
        self.demo = demo
        if demo:
            from sybl.tui.demo import DemoIpcClient

            self.ipc = DemoIpcClient()
        else:
            self.ipc = TuiIpcClient()
        self._log_cursor = 0
        self._event_task: asyncio.Task[None] | None = None
        self._daemon_connected = True
        self._connection_detail = ""
        self._listening_started_at: float | None = None
        self._last_status: dict = {}
        self._elapsed_timer: asyncio.TimerHandle | None = None
        self._demo_indicator = None

    def action_quit(self) -> None:
        self._shutdown_demo_indicator()
        self.exit()

    def _shutdown_demo_indicator(self) -> None:
        if self._demo_indicator is not None:
            self._demo_indicator.shutdown()
            self._demo_indicator = None

    def compose(self) -> ComposeResult:
        yield from ()

    async def on_mount(self) -> None:
        try:
            await self.ipc.connect()
        except IpcConnectionError as exc:
            self._daemon_connected = False
            self._connection_detail = str(exc)
        await self.push_screen("dashboard")
        if self._daemon_connected:
            await self._maybe_show_onboarding()
        self.run_worker(self._event_loop(), exclusive=False, thread=False)
        await self.refresh_dashboard()
        if self.demo:
            await self._start_demo_indicator()

    async def _start_demo_indicator(self) -> None:
        from sybl.config import ConfigManager
        from sybl.tui.demo_indicator import DemoIndicatorBridge

        config = ConfigManager().load()
        self._demo_indicator = DemoIndicatorBridge(config)
        if self._demo_indicator.active:
            status = self._last_status or await self.ipc.get_status()
            state = status.get("state", "idle")
            if isinstance(state, str):
                self._demo_indicator.on_state(state)

    def action_open_help(self) -> None:
        self.push_screen(HelpScreen())

    def _dashboard_screen(self) -> DashboardScreen | None:
        try:
            screen = self.get_screen("dashboard")
        except Exception:
            return None
        if not isinstance(screen, DashboardScreen) or not screen.is_mounted:
            return None
        return screen

    def _dashboard_widget(
        self,
        selector: str,
        expect_type: type[Widget],
    ) -> Widget | None:
        screen = self._dashboard_screen()
        if screen is None:
            return None
        try:
            widget = screen.query_one(selector, expect_type)
        except Exception:
            return None
        return widget

    async def _maybe_show_onboarding(self) -> None:
        config = await self.ipc.get_config()
        ui = config.get("ui", {})
        onboarding_done = isinstance(ui, dict) and ui.get("onboarding_complete", False)
        keys = await self.ipc.list_provider_keys()
        if not onboarding_done and not keys:
            completed = await self.push_screen_wait("onboarding")
            if completed:
                await self.refresh_dashboard()

    def _update_dashboard_shell(
        self,
        *,
        status: dict | None = None,
        connected: bool | None = None,
        banner: str | None = None,
    ) -> None:
        chrome = self._dashboard_widget("#chrome-bar", ChromeBar)
        context = self._dashboard_widget("#context-strip", ContextStrip)
        session = self._dashboard_widget("#session-pane", SessionPane)
        hero = self._dashboard_widget("#hero-band", HeroBand)
        live = self._dashboard_widget("#live-band", LiveBand)
        if None in (chrome, context, session, hero, live):
            return

        is_connected = self._daemon_connected if connected is None else connected
        if banner or not is_connected:
            offline_banner = banner or (
                self._connection_detail or "Daemon unreachable — run `sybl start`"
            )
            chrome.update_chrome(
                state="offline",
                connected=False,
                banner=offline_banner,
            )
            context.update_context(
                audio_device="-",
                provider="-",
                hotkey="-",
                connected=False,
                banner=offline_banner,
            )
            hero.update_state(state="offline", label=offline_banner)
            session.update_session(state="offline")
            live.update_live(state="offline")
            self._listening_started_at = None
            return

        status = status or {}
        state = str(status.get("state", "unknown"))
        provider = str(status.get("provider", "unknown"))
        hotkey = str(status.get("hotkey_binding", "unknown"))
        hotkey_mode = str(status.get("hotkey_mode", "both"))
        self._track_listening_state(state)

        stats = self._today_stats()
        chrome.update_chrome(
            state=state,
            connected=True,
            version=str(status.get("version", "")),
            uptime_seconds=self._as_float(status.get("uptime_seconds")),
            today_count=stats["dictations"],
        )
        context.update_context(
            audio_device=str(status.get("audio_device", "default")),
            provider=provider,
            hotkey=hotkey,
            hotkey_mode=hotkey_mode,
            connected=True,
        )

        elapsed = self._session_elapsed(state)
        hero.update_state(
            state=state,
            label=self._hero_label(state, provider, elapsed),
        )
        session.update_session(
            state=state,
            provider=provider,
            hotkey=hotkey,
            hotkey_mode=hotkey_mode,
            dictations=stats["dictations"],
            words=stats["words"],
            avg_latency=stats["avg_latency"],
            longest=stats["longest"],
        )
        live.update_live(
            state=state,
            last_text=stats["last_text"],
            duration=stats["last_duration"],
        )

    @staticmethod
    def _as_float(value: object) -> float | None:
        return float(value) if isinstance(value, (int, float)) else None

    @staticmethod
    def _hero_label(state: str, provider: str, elapsed: float | None) -> str:
        normalized = state.lower()
        if normalized == "listening":
            return f"recording · {elapsed:.1f}s" if elapsed else "recording…"
        if normalized == "processing":
            return f"{provider or 'provider'} · streaming"
        if normalized == "injecting":
            return "pasting into focused app"
        return "silent · waiting for hotkey"

    def _today_stats(self) -> dict:
        transcript_list = self._dashboard_widget("#transcript-list", TranscriptList)
        empty = {
            "dictations": 0,
            "words": 0,
            "avg_latency": "—",
            "longest": "—",
            "last_text": "",
            "last_duration": "",
        }
        if not isinstance(transcript_list, TranscriptList):
            return empty
        entries = transcript_list.entries
        if not entries:
            return empty
        texts = [str(e.get("final_text") or e.get("raw_text") or "") for e in entries]
        words = sum(len(t.split()) for t in texts)
        latencies = [
            float(e["latency_seconds"])
            for e in entries
            if isinstance(e.get("latency_seconds"), (int, float))
        ]
        durations = [
            float(e["audio_duration_seconds"])
            for e in entries
            if isinstance(e.get("audio_duration_seconds"), (int, float))
        ]
        last = entries[-1]
        last_duration = last.get("audio_duration_seconds")
        return {
            "dictations": len(entries),
            "words": words,
            "avg_latency": (
                f"{sum(latencies) / len(latencies):.2f}s" if latencies else "—"
            ),
            "longest": f"{max(durations):.1f}s" if durations else "—",
            "last_text": texts[-1],
            "last_duration": (
                f"{float(last_duration):.1f}s"
                if isinstance(last_duration, (int, float))
                else ""
            ),
        }

    def _track_listening_state(self, state: str) -> None:
        normalized = state.lower()
        if normalized == "listening":
            if self._listening_started_at is None:
                self._listening_started_at = time.monotonic()
        else:
            self._listening_started_at = None

    def _session_elapsed(self, state: str) -> float | None:
        if state.lower() != "listening" or self._listening_started_at is None:
            return None
        return time.monotonic() - self._listening_started_at

    async def refresh_dashboard(self) -> None:
        screen = self._dashboard_screen()
        if screen is None:
            return

        if not self._daemon_connected:
            self._update_dashboard_shell(banner=self._connection_detail)
            return

        try:
            status = await self.ipc.get_status()
        except IpcConnectionError as exc:
            self._daemon_connected = False
            self._connection_detail = str(exc)
            self._update_dashboard_shell(banner=str(exc))
            self.notify("Lost connection to daemon")
            return
        except Exception:
            logger.exception("Failed to refresh dashboard status")
            self.notify("Failed to refresh status from daemon")
            return

        self._daemon_connected = True
        self._last_status = status
        self._update_dashboard_shell(status=status)

        try:
            logs = await self.ipc.get_logs(after_cursor=0)
            log_band = screen.query_one("#log-band", LogBand)
            log_band.clear()
            for entry in logs.get("entries", []):
                if isinstance(entry, dict):
                    log_band.append_entry(
                        str(entry.get("level", "INFO")),
                        str(entry.get("message", "")),
                        timestamp=(
                            str(entry.get("timestamp"))
                            if entry.get("timestamp") is not None
                            else None
                        ),
                    )
            self._log_cursor = int(logs.get("cursor", 0))

            history = await self.ipc.get_history()
            transcript_list = screen.query_one("#transcript-list", TranscriptList)
            transcript_list.load_entries(history)
            self._update_dashboard_shell(status=status)
        except Exception:
            logger.exception("Failed to refresh logs/history")

    async def _event_loop(self) -> None:
        worker = get_current_worker()
        while not worker.is_cancelled:
            try:
                await self.ipc.connect()
                async for payload in self.ipc.stream_events():
                    if worker.is_cancelled:
                        return
                    self.post_message(IpcEventMessage(payload))
            except IpcConnectionError as exc:
                logger.debug("Event stream reconnecting: %s", exc)
                await asyncio.sleep(1.0)
            except Exception:
                logger.exception("Event stream error; reconnecting")
                await asyncio.sleep(1.0)

    def on_daemon_connection_message(self, message: DaemonConnectionMessage) -> None:
        self.run_worker(self.refresh_dashboard(), exclusive=False)

    def on_ipc_event_message(self, message: IpcEventMessage) -> None:
        payload = message.payload
        event_type = payload.get("type")
        if event_type == "state_changed":
            new_state = payload.get("state")
            if isinstance(new_state, str):
                status = dict(self._last_status)
                status["state"] = new_state
                self._last_status = status
                self._update_dashboard_shell(status=status)
                if self.demo and self._demo_indicator is not None:
                    self._demo_indicator.on_state(new_state)
            self.run_worker(self.refresh_dashboard(), exclusive=False)
        elif event_type == "level":
            value = payload.get("value")
            hero = self._dashboard_widget("#hero-band", HeroBand)
            if isinstance(value, (int, float)) and isinstance(hero, HeroBand):
                hero.update_meter(float(value))
            if self.demo and self._demo_indicator is not None and isinstance(
                value, (int, float)
            ):
                self._demo_indicator.on_level(float(value))
        elif event_type == "log_entry":
            entry = payload.get("entry", {})
            log_band = self._dashboard_widget("#log-band", LogBand)
            if isinstance(entry, dict) and isinstance(log_band, LogBand):
                log_band.append_entry(
                    str(entry.get("level", "INFO")),
                    str(entry.get("message", "")),
                    timestamp=(
                        str(entry.get("timestamp"))
                        if entry.get("timestamp") is not None
                        else None
                    ),
                )
            cursor = payload.get("cursor")
            if isinstance(cursor, int):
                self._log_cursor = cursor
        elif event_type == "transcript":
            entry = payload.get("entry", {})
            transcript_list = self._dashboard_widget("#transcript-list", TranscriptList)
            if isinstance(entry, dict) and isinstance(transcript_list, TranscriptList):
                transcript_list.append_entry(entry)
                if self._last_status:
                    self._update_dashboard_shell(status=self._last_status)
        elif event_type == "config_changed":
            self.run_worker(self.refresh_dashboard(), exclusive=False)


def run_tui(*, demo: bool = False) -> None:
    app = SyblTuiApp(demo=demo)
    app.run()
