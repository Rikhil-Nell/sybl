"""Hotkey manager interface and factory."""

from __future__ import annotations

import sys
from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import Protocol

from navi.config.models import HotkeyConfig


class HotkeyEvent(StrEnum):
    ACTIVATE = "activate"
    DEACTIVATE = "deactivate"
    CANCEL = "cancel"


HotkeyHandler = Callable[[HotkeyEvent], Awaitable[None]]


class HotkeyManager(Protocol):
    async def start(self, handler: HotkeyHandler) -> None: ...

    async def stop(self) -> None: ...


def create_hotkey_manager(config: HotkeyConfig) -> HotkeyManager:
    """Create a platform hotkey backend for the given config."""
    if config.mode != "ptt":
        msg = f"Unsupported hotkey mode: {config.mode!r}"
        raise ValueError(msg)

    if sys.platform == "win32":
        from navi.hotkeys.pynput_backend import PynputHotkeyManager

        return PynputHotkeyManager(config)

    msg = "Global hotkeys are Windows-only in Phase 4"
    raise NotImplementedError(msg)
