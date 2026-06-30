"""Cursor position helpers on Windows."""

from __future__ import annotations

import ctypes
import sys


class _Point(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class _Rect(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


class _MonitorInfo(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_ulong),
        ("rcMonitor", _Rect),
        ("rcWork", _Rect),
        ("dwFlags", ctypes.c_ulong),
    ]


_MONITOR_PRIMARY = 1
_MONITOR_NEAREST = 2


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


def get_primary_work_area() -> tuple[int, int, int, int]:
    """Return (left, top, right, bottom) of the primary monitor work area."""
    if sys.platform != "win32":
        return 0, 0, 1920, 1080
    user32 = ctypes.windll.user32
    origin = _Point(0, 0)
    monitor = user32.MonitorFromPoint(origin, _MONITOR_PRIMARY)
    info = _MonitorInfo()
    info.cbSize = ctypes.sizeof(_MonitorInfo)
    user32.GetMonitorInfoW(monitor, ctypes.byref(info))
    area = info.rcWork
    return area.left, area.top, area.right, area.bottom


def get_work_area_at(x: int, y: int) -> tuple[int, int, int, int]:
    """Return work area for the monitor nearest to (x, y)."""
    if sys.platform != "win32":
        return 0, 0, 1920, 1080
    user32 = ctypes.windll.user32
    point = _Point(x, y)
    monitor = user32.MonitorFromPoint(point, _MONITOR_NEAREST)
    info = _MonitorInfo()
    info.cbSize = ctypes.sizeof(_MonitorInfo)
    user32.GetMonitorInfoW(monitor, ctypes.byref(info))
    area = info.rcWork
    return area.left, area.top, area.right, area.bottom


def clamp_to_screen(x: int, y: int, width: int, height: int) -> tuple[int, int]:
    left, top, right, bottom = get_virtual_screen_bounds()
    max_x = max(left, right - width)
    max_y = max(top, bottom - height)
    return max(left, min(x, max_x)), max(top, min(y, max_y))


def center_top_position(
    work_area: tuple[int, int, int, int],
    width: int,
    margin_px: int,
) -> tuple[int, int]:
    """Return (x, y) for a top-center pill window origin."""
    left, top, right, _bottom = work_area
    x = left + (right - left - width) // 2
    return x, top + margin_px
