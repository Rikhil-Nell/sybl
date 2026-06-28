"""Windows clipboard paste text injection."""

from __future__ import annotations

import asyncio
import ctypes
import logging
import time
from ctypes import wintypes

from sybl.config.models import InjectConfig
from sybl.hotkeys.focus import FocusTarget
from sybl.inject.base import InjectError
from sybl.inject.focus_win import restore_focus

logger = logging.getLogger("sybl.inject.clipboard")

CF_UNICODETEXT = 13
GMEM_MOVEABLE = 0x0002
INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_V = 0x56
PASTE_SETTLE_SECONDS = 0.15
CLIPBOARD_OPEN_RETRIES = 5
CLIPBOARD_OPEN_DELAY_SECONDS = 0.05

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

ULONG_PTR = ctypes.c_size_t
SIZE_T = ctypes.c_size_t

user32.OpenClipboard.argtypes = [wintypes.HWND]
user32.OpenClipboard.restype = wintypes.BOOL
user32.CloseClipboard.argtypes = []
user32.CloseClipboard.restype = wintypes.BOOL
user32.IsClipboardFormatAvailable.argtypes = [wintypes.UINT]
user32.IsClipboardFormatAvailable.restype = wintypes.BOOL
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.GetClipboardData.restype = wintypes.HGLOBAL
user32.EmptyClipboard.argtypes = []
user32.EmptyClipboard.restype = wintypes.BOOL
user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HGLOBAL]
user32.SetClipboardData.restype = wintypes.HANDLE
user32.SendInput.argtypes = [wintypes.UINT, ctypes.c_void_p, ctypes.c_int]
user32.SendInput.restype = wintypes.UINT

kernel32.GlobalAlloc.argtypes = [wintypes.UINT, SIZE_T]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = wintypes.LPVOID
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalUnlock.restype = wintypes.BOOL
kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalFree.restype = wintypes.HGLOBAL


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", MOUSEINPUT),
        ("ki", KEYBDINPUT),
        ("hi", HARDWAREINPUT),
    ]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", wintypes.DWORD),
        ("union", INPUTUNION),
    ]


class _SkipRestore:
    """Sentinel when prior clipboard could not be read."""


_SKIP_RESTORE = _SkipRestore()


class ClipboardPasteInjector:
    """Inject text by setting the clipboard and simulating Ctrl+V."""

    def __init__(self, config: InjectConfig) -> None:
        self._config = config

    async def inject(self, text: str, target: FocusTarget | None) -> None:
        await asyncio.to_thread(self._inject_sync, text, target)

    def _inject_sync(self, text: str, target: FocusTarget | None) -> None:
        logger.info(
            "Injecting transcript (%d chars) into hwnd=%s",
            len(text),
            target.hwnd if target is not None else None,
        )
        prior_clipboard: str | None | _SkipRestore = None
        if self._config.restore_clipboard:
            prior_clipboard = read_clipboard_safe()

        try:
            set_clipboard(text)
            if target is not None:
                restore_focus(target)
            time.sleep(0.05)
            simulate_paste()
            # Target apps read the clipboard asynchronously; restoring too early
            # replaces the transcript before Ctrl+V is processed.
            time.sleep(PASTE_SETTLE_SECONDS)
        except InjectError:
            raise
        except Exception as exc:
            raise InjectError(f"Clipboard paste injection failed: {exc}") from exc

        if not self._config.restore_clipboard or prior_clipboard is _SKIP_RESTORE:
            return

        try:
            if prior_clipboard is None:
                clear_clipboard()
            else:
                set_clipboard(prior_clipboard)
        except InjectError as exc:
            logger.warning("Could not restore prior clipboard: %s", exc)


def read_clipboard_safe() -> str | None | _SkipRestore:
    try:
        return read_clipboard()
    except (InjectError, OSError) as exc:
        logger.warning("Could not read prior clipboard; skipping restore: %s", exc)
        return _SKIP_RESTORE


def _open_clipboard() -> None:
    for _ in range(CLIPBOARD_OPEN_RETRIES):
        if user32.OpenClipboard(None):
            return
        time.sleep(CLIPBOARD_OPEN_DELAY_SECONDS)
    raise InjectError("Could not open clipboard")


def read_clipboard() -> str | None:
    _open_clipboard()
    try:
        if not user32.IsClipboardFormatAvailable(CF_UNICODETEXT):
            return None

        handle = user32.GetClipboardData(CF_UNICODETEXT)
        if not handle:
            return None

        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            return None

        try:
            return ctypes.c_wchar_p(pointer).value
        finally:
            kernel32.GlobalUnlock(handle)
    finally:
        user32.CloseClipboard()


def set_clipboard(text: str) -> None:
    encoded = text.encode("utf-16-le") + b"\x00\x00"
    _open_clipboard()
    try:
        if not user32.EmptyClipboard():
            raise InjectError("Could not empty clipboard")

        handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        if not handle:
            raise InjectError("Could not allocate clipboard memory")

        pointer = kernel32.GlobalLock(handle)
        if not pointer:
            kernel32.GlobalFree(handle)
            raise InjectError("Could not lock clipboard memory")

        try:
            ctypes.memmove(pointer, encoded, len(encoded))
        finally:
            kernel32.GlobalUnlock(handle)

        if not user32.SetClipboardData(CF_UNICODETEXT, handle):
            kernel32.GlobalFree(handle)
            raise InjectError("Could not set clipboard data")
    finally:
        user32.CloseClipboard()


def clear_clipboard() -> None:
    _open_clipboard()
    try:
        if not user32.EmptyClipboard():
            raise InjectError("Could not clear clipboard")
    finally:
        user32.CloseClipboard()


def _keyboard_input(vk: int, *, key_up: bool = False) -> INPUT:
    entry = INPUT()
    entry.type = INPUT_KEYBOARD
    entry.union.ki = KEYBDINPUT(
        wVk=vk,
        wScan=0,
        dwFlags=KEYEVENTF_KEYUP if key_up else 0,
        time=0,
        dwExtraInfo=0,
    )
    return entry


def simulate_paste() -> None:
    """Simulate Ctrl+V via SendInput (avoids pynput deadlocks with hotkey listener)."""
    inputs = (INPUT * 4)(
        _keyboard_input(VK_CONTROL),
        _keyboard_input(VK_V),
        _keyboard_input(VK_V, key_up=True),
        _keyboard_input(VK_CONTROL, key_up=True),
    )
    sent = user32.SendInput(4, ctypes.byref(inputs), ctypes.sizeof(INPUT))
    if sent != 4:
        raise InjectError(f"SendInput paste failed (sent {sent}/4 events)")
