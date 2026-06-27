"""Restore keyboard focus on Windows."""

from __future__ import annotations

import ctypes
import logging

from navi.hotkeys.focus import FocusTarget

logger = logging.getLogger("navi.inject.focus")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32


def restore_focus(target: FocusTarget) -> bool:
    """Try to restore focus to the captured window handle."""
    if target.hwnd is None:
        return False

    hwnd = target.hwnd
    if user32.GetForegroundWindow() == hwnd:
        return True

    current_thread = kernel32.GetCurrentThreadId()
    foreground = user32.GetForegroundWindow()
    foreground_thread = user32.GetWindowThreadProcessId(foreground, None)
    target_thread = user32.GetWindowThreadProcessId(hwnd, None)

    attached_foreground = False
    attached_target = False

    try:
        if foreground_thread and foreground_thread != current_thread:
            attached_foreground = bool(
                user32.AttachThreadInput(foreground_thread, current_thread, True)
            )
        if target_thread and target_thread != current_thread:
            attached_target = bool(
                user32.AttachThreadInput(target_thread, current_thread, True)
            )

        user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        result = bool(user32.SetForegroundWindow(hwnd))
        if not result:
            logger.warning(
                "SetForegroundWindow failed for hwnd=%s title=%r",
                target.hwnd,
                target.title,
            )
        return result
    finally:
        if attached_target:
            user32.AttachThreadInput(target_thread, current_thread, False)
        if attached_foreground:
            user32.AttachThreadInput(foreground_thread, current_thread, False)
