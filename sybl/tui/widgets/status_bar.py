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
    StatusBar.disconnected {
        background: $error;
        color: $text;
    }
    """

    def update_status(
        self,
        *,
        state: str,
        provider: str,
        hotkey: str,
        hotkey_mode: str = "ptt",
        audio_device: str,
        connected: bool = True,
        banner: str | None = None,
    ) -> None:
        device = audio_device or "default"
        if banner:
            self.set_class(not connected, "disconnected")
            self.update(banner)
            return
        self.set_class(not connected, "disconnected")
        self.update(
            f"State: {state} | Provider: {provider} | "
            f"Hotkey: {hotkey} ({hotkey_mode}) | Mic: {device}"
        )
