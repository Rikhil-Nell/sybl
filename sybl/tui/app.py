"""Textual TUI application."""

from __future__ import annotations

import asyncio

from textual.app import App, ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.worker import get_current_worker

from sybl.ipc.protocol import decode_line
from sybl.tui.client import TuiIpcClient
from sybl.tui.screens.dashboard import DashboardScreen
from sybl.tui.screens.onboarding import OnboardingScreen
from sybl.tui.screens.settings import SettingsScreen
from sybl.tui.widgets.history_panel import HistoryPanel
from sybl.tui.widgets.log_view import LogView
from sybl.tui.widgets.status_bar import StatusBar


class IpcEventMessage(Message):
    def __init__(self, payload: dict) -> None:
        super().__init__()
        self.payload = payload


class SyblTuiApp(App):
    TITLE = "sybl"
    CSS = """
    .panel-title {
        height: 1;
        padding: 0 1;
        background: $boost;
    }
    #settings-form {
        padding: 1 2;
        height: auto;
    }
    #onboarding-body {
        padding: 1 2;
        height: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
    ]

    SCREENS = {
        "dashboard": DashboardScreen,
        "settings": SettingsScreen,
        "onboarding": OnboardingScreen,
    }

    def __init__(self) -> None:
        super().__init__()
        self.ipc = TuiIpcClient()
        self._log_cursor = 0
        self._event_task: asyncio.Task[None] | None = None

    def compose(self) -> ComposeResult:
        yield from ()

    async def on_mount(self) -> None:
        await self.ipc.connect()
        await self.push_screen("dashboard")
        await self._maybe_show_onboarding()
        self.run_worker(self._event_loop(), exclusive=False, thread=False)

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

    async def refresh_dashboard(self) -> None:
        screen = self._dashboard_screen()
        if screen is None:
            return

        try:
            status = await self.ipc.get_status()
        except Exception:
            return

        status_bar = screen.query_one("#status-bar", StatusBar)
        status_bar.update_status(
            state=str(status.get("state", "unknown")),
            provider=str(status.get("provider", "unknown")),
            hotkey=str(status.get("hotkey_binding", "unknown")),
            audio_device=str(status.get("audio_device", "default")),
        )

        logs = await self.ipc.get_logs(after_cursor=0)
        log_view = screen.query_one("#log-view", LogView)
        log_view.clear()
        for entry in logs.get("entries", []):
            if isinstance(entry, dict):
                log_view.append_entry(
                    str(entry.get("level", "INFO")),
                    str(entry.get("message", "")),
                )
        self._log_cursor = int(logs.get("cursor", 0))

        history = await self.ipc.get_history()
        history_panel = screen.query_one("#history-panel", HistoryPanel)
        history_panel.load_entries(history)

    async def _event_loop(self) -> None:
        worker = get_current_worker()
        while not worker.is_cancelled:
            try:
                reader = await self.ipc.connect_event_reader()
                while not worker.is_cancelled:
                    line = await reader.readline()
                    if not line:
                        break
                    payload = decode_line(line)
                    self.post_message(IpcEventMessage(payload))
            except Exception:
                await asyncio.sleep(1.0)

    def on_ipc_event_message(self, message: IpcEventMessage) -> None:
        payload = message.payload
        event_type = payload.get("type")
        if event_type == "state_changed":
            self.run_worker(self.refresh_dashboard(), exclusive=False)
        elif event_type == "log_entry":
            entry = payload.get("entry", {})
            log_view = self._dashboard_widget("#log-view", LogView)
            if isinstance(entry, dict) and isinstance(log_view, LogView):
                log_view.append_entry(
                    str(entry.get("level", "INFO")),
                    str(entry.get("message", "")),
                )
            cursor = payload.get("cursor")
            if isinstance(cursor, int):
                self._log_cursor = cursor
        elif event_type == "transcript":
            entry = payload.get("entry", {})
            history_panel = self._dashboard_widget("#history-panel", HistoryPanel)
            if isinstance(entry, dict) and isinstance(history_panel, HistoryPanel):
                history_panel.append_entry(entry)
        elif event_type == "config_changed":
            self.run_worker(self.refresh_dashboard(), exclusive=False)


def run_tui() -> None:
    app = SyblTuiApp()
    app.run()
