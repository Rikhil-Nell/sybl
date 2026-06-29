"""Session detail pane: pipeline, provider, hotkey, and today's stats."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Static

# (glyph-key, stage label, detail template) in pipeline order.
_STAGES: list[tuple[str, str, str]] = [
    ("capture", "capture", "16 kHz mono int16"),
    ("transcribe", "transcribe", "{provider} · streaming"),
    ("cleanup", "cleanup", "trim · capitalize · punctuate"),
    ("inject", "inject", "paste · restore clipboard"),
]

# Which pipeline stage is "active" for a given session state (-1 == none).
_STATE_ACTIVE: dict[str, int] = {
    "idle": -1,
    "offline": -1,
    "listening": 0,
    "processing": 1,
    "injecting": 3,
}

_TEXT = "#e8e4d9"
_DIM = "#9aa6c0"
_MUTED = "#6b7a99"
_GOLD = "#d8b43a"
_GREEN = "#5fae7f"


def _kv(rows: list[tuple[str, str]]) -> str:
    return "\n".join(f"[{_MUTED}]{key:<11}[/] {value}" for key, value in rows)


class SessionPane(Vertical):
    """Left dashboard column: live pipeline + provider/hotkey/today context."""

    def compose(self) -> ComposeResult:
        yield Static("Session", classes="panel-header")
        with VerticalScroll(id="session-body"):
            yield Static("PIPELINE", classes="section-title section-title-first")
            yield Static("", id="session-pipeline")
            yield Static("PROVIDER", classes="section-title")
            yield Static("", id="session-provider")
            yield Static("HOTKEY", classes="section-title")
            yield Static("", id="session-hotkey")
            yield Static("TODAY", classes="section-title")
            yield Static("", id="session-today")

    def on_mount(self) -> None:
        self.update_session(state="idle")

    def update_session(
        self,
        *,
        state: str,
        provider: str = "",
        fallback: str = "",
        hotkey: str = "",
        hotkey_mode: str = "both",
        cancel_binding: str = "esc",
        dictations: int | None = None,
        words: int | None = None,
        avg_latency: str = "—",
        longest: str = "—",
    ) -> None:
        normalized = state.lower()
        self.query_one("#session-pipeline", Static).update(
            self._render_pipeline(normalized, provider or "provider")
        )
        self.query_one("#session-provider", Static).update(
            _kv(
                [
                    ("active", f"[{_TEXT}]{provider or '—'}[/]"),
                    ("fallback", f"[{_DIM}]{fallback or '—'}[/]"),
                ]
            )
        )
        mode_value = f"[{_TEXT}]{hotkey_mode}[/] [{_MUTED}]hold=PTT · 2×=toggle[/]"
        self.query_one("#session-hotkey", Static).update(
            _kv(
                [
                    ("mode", mode_value),
                    ("activate", f"[{_DIM}]{hotkey or '—'}[/]"),
                    ("cancel", f"[{_DIM}]{cancel_binding}[/]"),
                ]
            )
        )
        dictations_value = 0 if dictations is None else dictations
        words_value = 0 if words is None else words
        self.query_one("#session-today", Static).update(
            _kv(
                [
                    ("dictations", f"[{_TEXT}]{dictations_value}[/]"),
                    ("words", f"[{_TEXT}]{words_value:,}[/]"),
                    ("avg latency", f"[{_DIM}]{avg_latency}[/]"),
                    ("longest", f"[{_DIM}]{longest}[/]"),
                ]
            )
        )

    def _render_pipeline(self, state: str, provider: str) -> str:
        active = _STATE_ACTIVE.get(state, -1)
        lines: list[str] = []
        for index, (_key, stage, detail) in enumerate(_STAGES):
            if active >= 0 and index < active:
                glyph, glyph_color = "✓", _GREEN
            elif active >= 0 and index == active:
                glyph, glyph_color = "●", _GOLD
            else:
                glyph, glyph_color = "○", _MUTED
            stage_color = _GOLD if index == active else _DIM
            rendered_detail = detail.format(provider=provider)
            lines.append(
                f"[{glyph_color}]{glyph}[/] "
                f"[{stage_color}]{stage:<10}[/] "
                f"[{_MUTED}]{rendered_detail}[/]"
            )
        return "\n".join(lines)
