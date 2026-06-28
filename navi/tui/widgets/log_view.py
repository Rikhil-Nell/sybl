"""Live log tail widget."""

from __future__ import annotations

from textual.widgets import RichLog


class LogView(RichLog):
    DEFAULT_CSS = """
    LogView {
        border: solid $primary;
        height: 1fr;
    }
    """

    def append_entry(self, level: str, message: str) -> None:
        self.write(f"[{level}] {message}")
