"""Full-width log band with timestamp and level coloring."""

from __future__ import annotations

from datetime import datetime

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import RichLog, Static


def _format_timestamp(raw: str | None) -> str:
    if not raw:
        return datetime.now().strftime("%H:%M:%S")
    try:
        parsed = datetime.fromisoformat(raw)
        return parsed.strftime("%H:%M:%S")
    except ValueError:
        return raw[:8] if len(raw) >= 8 else raw


def _level_class(level: str) -> str:
    normalized = level.upper()
    if normalized in ("WARNING", "WARN"):
        return "log-warning"
    if normalized in ("ERROR", "CRITICAL"):
        return "log-error"
    if normalized == "DEBUG":
        return "log-debug"
    return "log-info"


class LogBand(Vertical):
    """Ring-buffer log tail with level-colored rows."""

    def compose(self) -> ComposeResult:
        yield Static("Logs", classes="panel-header")
        yield RichLog(id="log-band-view", highlight=False, markup=True, wrap=True)

    def clear(self) -> None:
        self.query_one("#log-band-view", RichLog).clear()

    def append_entry(
        self,
        level: str,
        message: str,
        *,
        timestamp: str | None = None,
    ) -> None:
        ts = _format_timestamp(timestamp)
        level_upper = level.upper()
        css = _level_class(level)
        line = f"[log-time]{ts}[/] [{css}]{level_upper}[/] {message}"
        self.query_one("#log-band-view", RichLog).write(line)
