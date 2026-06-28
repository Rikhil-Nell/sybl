"""Transcription history list widget."""

from __future__ import annotations

from textual.widgets import Label, ListItem, ListView


class HistoryPanel(ListView):
    DEFAULT_CSS = """
    HistoryPanel {
        border: solid $secondary;
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._entries: list[dict] = []

    def load_entries(self, entries: list[dict]) -> None:
        self._entries = list(entries)
        self.clear()
        for entry in self._entries:
            self._append_item(entry)

    def append_entry(self, entry: dict) -> None:
        self._entries.append(entry)
        self._append_item(entry)

    def _append_item(self, entry: dict) -> None:
        text = str(entry.get("final_text") or entry.get("raw_text") or "")
        provider = str(entry.get("provider", ""))
        label = text if len(text) <= 80 else f"{text[:77]}..."
        self.append(ListItem(Label(f"{label} ({provider})")))

    @property
    def entries(self) -> list[dict]:
        return list(self._entries)

    def selected_entry(self) -> dict | None:
        if self.index is None or self.index >= len(self._entries):
            return None
        return self._entries[self.index]
