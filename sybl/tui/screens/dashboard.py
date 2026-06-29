"""Main dashboard screen."""

from __future__ import annotations

import asyncio
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Input, ListView

from sybl.config import ConfigError, ConfigManager
from sybl.tui.screens.help import HelpScreen
from sybl.tui.screens.settings import SettingsScreen
from sybl.tui.widgets.chrome_bar import ChromeBar
from sybl.tui.widgets.context_strip import ContextStrip
from sybl.tui.widgets.hero_band import HeroBand
from sybl.tui.widgets.key_footer import KeyFooter
from sybl.tui.widgets.live_band import LiveBand
from sybl.tui.widgets.log_band import LogBand
from sybl.tui.widgets.session_pane import SessionPane
from sybl.tui.widgets.transcript_list import TranscriptList


class DashboardScreen(Screen):
    BINDINGS = [
        ("s", "open_settings", "Settings"),
        ("e", "edit_config", "Edit config"),
        ("question_mark", "open_help", "Help"),
        ("slash", "focus_filter", "Filter"),
        ("y", "copy_selected", "Copy"),
    ]

    def compose(self) -> ComposeResult:
        with Vertical(id="dashboard-main"):
            yield ChromeBar(id="chrome-bar")
            yield ContextStrip(id="context-strip")
            yield HeroBand(id="hero-band")
            with Horizontal(id="dashboard-panes"):
                yield SessionPane(id="session-pane")
                with Vertical(id="right-column"):
                    yield TranscriptList(id="transcript-list")
                    yield LogBand(id="log-band")
            yield LiveBand(id="live-band")
            yield KeyFooter(id="key-footer")

    async def on_mount(self) -> None:
        await self.app.refresh_dashboard()
        # Focus the list, never the filter input — otherwise single-key
        # bindings (s, ?, y, q) get typed into the search box instead.
        try:
            self.query_one("#transcript-list-view", ListView).focus()
        except Exception:
            pass

    def action_focus_filter(self) -> None:
        try:
            self.query_one("#transcript-filter", Input).focus()
        except Exception:
            pass

    def action_open_settings(self) -> None:
        self.app.push_screen(SettingsScreen())

    def action_edit_config(self) -> None:
        from sybl.config.edit import EditorError, ensure_config_file, open_in_editor

        path = ensure_config_file()
        try:
            with self.app.suspend():
                open_in_editor(path)
        except EditorError as exc:
            self.app.notify(str(exc), severity="error")
            return
        self.app.run_worker(self._reload_after_edit(path), exclusive=False)

    async def _reload_after_edit(self, path: Path) -> None:
        if getattr(self.app, "demo", False):
            self.app.notify(f"Edited {path.name} (demo mode — not applied)")
            return
        try:
            config = await asyncio.to_thread(lambda: ConfigManager().load())
        except ConfigError as exc:
            self.app.notify(f"Config invalid: {exc}", severity="error")
            return
        try:
            await self.app.ipc.patch_config(config.model_dump(mode="json"))
        except Exception as exc:  # noqa: BLE001 - surface any reload failure to user
            self.app.notify(
                f"Saved, but daemon reload failed: {exc}",
                severity="warning",
            )
            return
        await self.app.refresh_dashboard()
        self.app.notify("Reloaded config from file")

    def action_open_help(self) -> None:
        self.app.push_screen(HelpScreen())

    def action_copy_selected(self) -> None:
        panel = self.query_one("#transcript-list", TranscriptList)
        entry = panel.selected_entry()
        if entry is None:
            return
        text = str(entry.get("final_text") or entry.get("raw_text") or "")
        if text:
            self.app.copy_to_clipboard(text)
            self.app.notify("Copied transcript to clipboard")
