"""Selectable transcript history with client-side filter."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.widgets import Input, Label, ListItem, ListView, Static

_MUTED = "#6b7a99"


def _entry_text(entry: dict) -> str:
    return str(entry.get("final_text") or entry.get("raw_text") or "")


class TranscriptList(Vertical):
    """History list with filter input and a words/duration/provider suffix."""

    def compose(self) -> ComposeResult:
        yield Static("Transcripts", id="transcript-header", classes="panel-header")
        yield Input(placeholder="/ filter…", id="transcript-filter")
        yield ListView(id="transcript-list-view")

    def on_mount(self) -> None:
        self._entries: list[dict] = []
        self._filter_text = ""
        self._update_header()

    def on_key(self, event: events.Key) -> None:
        # Esc inside the filter returns focus to the list instead of trapping
        # the cursor in the search box.
        if event.key == "escape":
            filter_input = self.query_one("#transcript-filter", Input)
            if filter_input.has_focus:
                self.query_one("#transcript-list-view", ListView).focus()
                event.stop()

    def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "transcript-filter":
            return
        self._filter_text = event.value.strip().lower()
        self._rebuild_list()

    def load_entries(self, entries: list[dict]) -> None:
        self._entries = list(entries)
        self._rebuild_list()

    def append_entry(self, entry: dict) -> None:
        self._entries.append(entry)
        if self._matches_filter(entry):
            self._append_item(entry)
        self._update_header()

    def _matches_filter(self, entry: dict) -> bool:
        if not self._filter_text:
            return True
        return self._filter_text in _entry_text(entry).lower()

    def _visible_entries(self) -> list[dict]:
        return [e for e in self._entries if self._matches_filter(e)]

    def _rebuild_list(self) -> None:
        list_view = self.query_one("#transcript-list-view", ListView)
        list_view.clear()
        for entry in self._entries:
            if self._matches_filter(entry):
                self._append_item(entry)
        self._update_header()

    def _update_header(self) -> None:
        try:
            header = self.query_one("#transcript-header", Static)
        except Exception:
            return
        count = len(self._visible_entries())
        header.update(f"Transcripts   [{_MUTED}]{count} · ↑↓ select[/]")

    def _append_item(self, entry: dict) -> None:
        text = _entry_text(entry)
        words = len(text.split())
        duration = entry.get("audio_duration_seconds")
        duration_label = (
            f"{float(duration):.1f}s" if isinstance(duration, (int, float)) else "—"
        )
        provider = str(entry.get("provider") or "—")
        label = text if len(text) <= 60 else f"{text[:59]}…"
        meta = f"{words}w · {duration_label} · {provider}"
        list_view = self.query_one("#transcript-list-view", ListView)
        list_view.append(
            ListItem(Label(f"· {label}  [{_MUTED}]{meta}[/]", classes="transcript-row"))
        )

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)

    def selected_entry(self) -> dict | None:
        list_view = self.query_one("#transcript-list-view", ListView)
        visible = self._visible_entries()
        if list_view.index is None or list_view.index >= len(visible):
            return None
        return visible[list_view.index]

    def last_latency(self) -> float | None:
        for entry in reversed(self._entries):
            latency = entry.get("latency_seconds")
            if isinstance(latency, (int, float)):
                return float(latency)
        return None
