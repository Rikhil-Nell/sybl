"""Live band: streaming partial while active, last injected text when idle."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static

_TEXT = "#e8e4d9"
_MUTED = "#6b7a99"
_GOLD = "#d8b43a"


def _truncate(text: str, limit: int = 120) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


class LiveBand(Static):
    """Bottom band echoing the current/last transcript, like a live ticker."""

    def compose(self) -> ComposeResult:
        with Horizontal(classes="live-head"):
            yield Static("Last dictation", id="live-title")
            yield Static("", id="live-dur")
        yield Static("", id="live-line")

    def on_mount(self) -> None:
        self.update_live(state="idle")

    def update_live(
        self,
        *,
        state: str,
        last_text: str = "",
        duration: str = "",
    ) -> None:
        normalized = state.lower()
        title = self.query_one("#live-title", Static)
        line = self.query_one("#live-line", Static)
        self.query_one("#live-dur", Static).update(duration)

        if normalized == "listening":
            title.update("Live transcript")
            said = _truncate(last_text) if last_text else "listening…"
            line.update(f"[{_MUTED}]{said}[/] [{_GOLD}]▌[/]")
        elif normalized == "processing":
            title.update("Live transcript")
            said = _truncate(last_text) if last_text else "transcribing…"
            line.update(f"[{_TEXT}]{said}[/]")
        elif normalized == "injecting":
            title.update("Injecting")
            said = _truncate(last_text)
            line.update(
                f"[{_MUTED}]→ paste:[/] [{_TEXT}]“{said}”[/]"
                if last_text
                else f"[{_MUTED}]pasting…[/]"
            )
        else:
            title.update("Last dictation")
            if last_text:
                line.update(
                    f"[{_MUTED}]idle — last injected:[/] "
                    f"[{_TEXT}]“{_truncate(last_text)}”[/]"
                )
            else:
                line.update(
                    f"[{_MUTED}]no dictations yet — hold your hotkey to start[/]"
                )
