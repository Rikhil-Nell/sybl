"""Cursor position helpers on Windows."""

from __future__ import annotations

import ctypes


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


def get_cursor_pos() -> tuple[int, int]:
    point = _Point()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(point))
    return point.x, point.y


def get_virtual_screen_bounds() -> tuple[int, int, int, int]:
    user32 = ctypes.windll.user32
    x = user32.GetSystemMetrics(76)  # SM_XVIRTUALSCREEN
    y = user32.GetSystemMetrics(77)  # SM_YVIRTUALSCREEN
    width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return x, y, x + width, y + height


def clamp_to_screen(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    left, top, right, bottom = get_virtual_screen_bounds()
    max_x = max(left, right - width)
    max_y = max(top, bottom - height)
    return max(left, min(x, max_x)), max(top, min(y, max_y))
