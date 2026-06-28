"""Main dashboard screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Footer, Header, Static

from sybl.tui.widgets.history_panel import HistoryPanel
from sybl.tui.widgets.log_view import LogView
from sybl.tui.widgets.status_bar import StatusBar


class DashboardScreen(Screen):
    BINDINGS = [
        ("s", "open_settings", "Settings"),
        ("r", "refresh", "Refresh"),
        ("y", "copy_selected", "Copy"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield StatusBar(id="status-bar")
        with Horizontal():
            with Vertical():
                yield Static("Logs", classes="panel-title")
                yield LogView(id="log-view", highlight=True, markup=False)
            with Vertical():
                yield Static("History", classes="panel-title")
                yield HistoryPanel(id="history-panel")
        yield Footer()

    async def on_mount(self) -> None:
        await self.app.refresh_dashboard()

    def action_open_settings(self) -> None:
        self.app.push_screen("settings")

    def action_refresh(self) -> None:
        self.run_worker(self.app.refresh_dashboard(), exclusive=False)

    def action_copy_selected(self) -> None:
        panel = self.query_one("#history-panel", HistoryPanel)
        entry = panel.selected_entry()
        if entry is None:
            return
        text = str(entry.get("final_text") or entry.get("raw_text") or "")
        if text:
            self.app.copy_to_clipboard(text)
            self.app.notify("Copied transcript to clipboard")
