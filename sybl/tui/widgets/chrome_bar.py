"""Top chrome bar: brand, daemon chip, state, and version/uptime/today meta."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


def _format_uptime(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    total = int(seconds)
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    if hours:
        return f"{hours}h{minutes:02d}m"
    if minutes:
        return f"{minutes}m"
    return f"{total}s"


class ChromeBar(Horizontal):
    """Identity row: ``✦ sybl  ● live  idle … v0.1.2 · up 2h14m · 38 today``."""

    def compose(self) -> ComposeResult:
        yield Static("✦", id="chrome-logo")
        yield Static("sybl", id="chrome-brand")
        yield Static("● offline", id="daemon-chip")
        yield Static("idle", id="state-chip")
        yield Static("", id="chrome-meta")

    def update_chrome(
        self,
        *,
        state: str,
        connected: bool,
        banner: str | None = None,
        version: str = "",
        uptime_seconds: float | None = None,
        today_count: int | None = None,
    ) -> None:
        daemon = self.query_one("#daemon-chip", Static)
        state_chip = self.query_one("#state-chip", Static)
        meta = self.query_one("#chrome-meta", Static)

        if banner or not connected:
            daemon.update("● offline")
            daemon.set_class(False, "live")
            daemon.set_class(True, "offline")
            state_chip.update("offline")
            for cls in ("listening", "processing", "injecting"):
                state_chip.set_class(False, cls)
            meta.update("")
            return

        daemon.update("● live")
        daemon.set_class(True, "live")
        daemon.set_class(False, "offline")

        normalized = state.lower()
        state_chip.update(normalized)
        for cls in ("listening", "processing", "injecting"):
            state_chip.set_class(normalized == cls, cls)

        parts: list[str] = []
        if version:
            parts.append(f"v{version}")
        parts.append(f"up [#9aa6c0]{_format_uptime(uptime_seconds)}[/]")
        if today_count is not None:
            parts.append(f"[#9aa6c0]{today_count}[/] today")
        meta.update("  ·  ".join(parts))
