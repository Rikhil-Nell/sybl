"""Text injection interface and factory."""

from __future__ import annotations

import sys
from typing import Protocol

from navi.config.models import NaviConfig
from navi.hotkeys.focus import FocusTarget


class InjectError(Exception):
    """Raised when text cannot be injected into the target application."""


class TextInjector(Protocol):
    async def inject(self, text: str, target: FocusTarget | None) -> None: ...


def create_injector(config: NaviConfig) -> TextInjector:
    """Create a platform text injector for the configured strategy."""
    if config.inject.strategy != "paste":
        msg = f"Unsupported injection strategy: {config.inject.strategy!r}"
        raise NotImplementedError(msg)

    if sys.platform == "win32":
        from navi.inject.clipboard_win import ClipboardPasteInjector

        return ClipboardPasteInjector(config.inject)

    msg = "Text injection is Windows-only in Phase 5"
    raise NotImplementedError(msg)
