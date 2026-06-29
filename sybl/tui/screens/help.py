"""Keyboard help overlay."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

_HELP_ROWS = [
    ("s", "Open settings"),
    ("?", "Show this help"),
    ("y", "Copy selected transcript"),
    ("↑ / ↓", "Navigate transcripts"),
    ("q", "Quit TUI"),
    ("Esc", "Dismiss modal (settings / help)"),
]


class HelpScreen(ModalScreen[None]):
    BINDINGS = [("escape", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with Vertical(id="help-modal"):
            yield Static("Keyboard shortcuts", id="help-title")
            for key, description in _HELP_ROWS:
                yield Static(
                    f"[help-key]{key:<8}[/]{description}",
                    classes="help-row",
                )

    def action_dismiss(self) -> None:
        self.dismiss(None)
