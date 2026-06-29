"""Context strip: mic, provider, hotkey, IPC status."""

from __future__ import annotations

from textual.widgets import Static


class ContextStrip(Static):
    """Device and binding context — not session state."""

    def update_context(
        self,
        *,
        audio_device: str,
        provider: str,
        hotkey: str,
        hotkey_mode: str = "both",
        connected: bool = True,
        banner: str | None = None,
    ) -> None:
        if banner:
            self.set_class(True, "disconnected")
            self.update(banner)
            return
        self.set_class(not connected, "disconnected")
        device = audio_device or "default"
        hotkey_label = f"{hotkey_mode} · {hotkey}"
        self.update(
            f"Mic: [bold]{device}[/]  ·  "
            f"Provider: [bold]{provider}[/]  ·  "
            f"Hotkey: [bold]{hotkey_label}[/]  ·  "
            f"IPC: [bold]{'connected' if connected else 'offline'}[/]"
        )
