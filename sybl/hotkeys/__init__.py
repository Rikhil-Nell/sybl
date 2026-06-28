"""Global hotkey listener (Phase 4)."""

from sybl.hotkeys.base import HotkeyEvent, HotkeyManager, create_hotkey_manager
from sybl.hotkeys.bindings import BindingParseError, ParsedBinding, parse_binding
from sybl.hotkeys.focus import FocusTarget, capture_foreground

__all__ = [
    "BindingParseError",
    "FocusTarget",
    "HotkeyEvent",
    "HotkeyManager",
    "ParsedBinding",
    "capture_foreground",
    "create_hotkey_manager",
    "parse_binding",
]
