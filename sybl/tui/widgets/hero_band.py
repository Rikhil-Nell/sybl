"""Hero status band: the dashboard anchor — state, live RMS meter, hint."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static

_STATE_GLYPH: dict[str, str] = {
    "idle": "◌",
    "listening": "●",
    "processing": "●",
    "injecting": "●",
    "offline": "○",
}

_DEFAULT_HINT: dict[str, str] = {
    "idle": "hold hotkey · double-press to toggle",
    "listening": "Esc cancels · release to send",
    "processing": "transcribing…",
    "injecting": "pasting into focused app",
    "offline": "daemon unreachable — run `sybl start`",
}

_BAR_CELLS = 30
_ON_COLOR: dict[str, str] = {
    "listening": "#d8b43a",
    "processing": "#5a8fc4",
    "injecting": "#5a8fc4",
}
_OFF_COLOR = "#3a4f80"


class HeroBand(Horizontal):
    """Full-width status band: ``◌ IDLE   ▱▱▱   hint``.

    The RMS meter is rendered as colored block glyphs so it reads like the
    web mock; ``update_meter`` is driven by the daemon ``level`` IPC event.
    """

    def compose(self) -> ComposeResult:
        yield Static("◌ IDLE", id="hero-state")
        with Vertical(id="hero-meter-wrap"):
            yield Static("", id="hero-meter")
            yield Static("silent · waiting for hotkey", id="hero-meter-label")
        yield Static(_DEFAULT_HINT["idle"], id="hero-hint")

    def on_mount(self) -> None:
        self._state = "idle"
        self.meter_value = 0.0
        self._render_meter()

    def update_state(
        self,
        *,
        state: str,
        label: str | None = None,
        hint: str | None = None,
    ) -> None:
        normalized = state.lower()
        self._state = normalized

        glyph = _STATE_GLYPH.get(normalized, "○")
        self.query_one("#hero-state", Static).update(f"{glyph} {normalized.upper()}")
        for cls in ("listening", "processing", "injecting", "offline"):
            self.set_class(normalized == cls, cls)

        self.query_one("#hero-meter-label", Static).update(label or "")
        self.query_one("#hero-hint", Static).update(
            hint if hint is not None else _DEFAULT_HINT.get(normalized, "")
        )

        if normalized not in ("listening", "processing"):
            self.update_meter(0.0)

    def update_meter(self, value: float) -> None:
        self.meter_value = max(0.0, min(1.0, float(value)))
        self._render_meter()

    def _render_meter(self) -> None:
        filled = round(self.meter_value * _BAR_CELLS)
        on = "▰" * filled
        off = "▱" * (_BAR_CELLS - filled)
        on_color = _ON_COLOR.get(self._state, "#6b7a99")
        try:
            self.query_one("#hero-meter", Static).update(
                f"[{on_color}]{on}[/][{_OFF_COLOR}]{off}[/]"
            )
        except Exception:
            pass
