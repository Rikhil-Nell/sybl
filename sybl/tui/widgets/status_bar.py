"""Status bar widget."""

from __future__ import annotations

from textual.widgets import Static


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: $surface;
        color: $text;
        padding: 0 1;
    }
    """

    def update_status(
        self,
        *,
        state: str,
        provider: str,
        hotkey: str,
        audio_device: str,
    ) -> None:
        device = audio_device or "default"
        self.update(
            f"State: {state} | Provider: {provider} | Hotkey: {hotkey} | Mic: {device}"
        )
