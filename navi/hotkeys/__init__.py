"""Global hotkey listener (Phase 4)."""

from navi.hotkeys.base import HotkeyEvent, HotkeyManager, create_hotkey_manager
from navi.hotkeys.bindings import BindingParseError, ParsedBinding, parse_binding
from navi.hotkeys.focus import FocusTarget, capture_foreground

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
