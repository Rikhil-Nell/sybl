"""Capture the focused window at dictation activation time."""

from __future__ import annotations

import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class FocusTarget:
    """Foreground target captured when the user activates dictation."""

    hwnd: int | None = None
    pid: int | None = None
    title: str | None = None


def capture_foreground() -> FocusTarget:
    """Return the currently focused window, when supported on this platform."""
    if sys.platform == "win32":
        return _capture_windows()
    return FocusTarget()


def _capture_windows() -> FocusTarget:
    import ctypes
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return FocusTarget()

    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))

    length = user32.GetWindowTextLengthW(hwnd) + 1
    buffer = ctypes.create_unicode_buffer(length)
    user32.GetWindowTextW(hwnd, buffer, length)

    return FocusTarget(
        hwnd=int(hwnd),
        pid=int(pid.value),
        title=buffer.value or None,
    )
