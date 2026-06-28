"""Windows global hotkey backend using pynput."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from pynput import keyboard

from sybl.config.models import HotkeyConfig
from sybl.hotkeys.base import HotkeyEvent, HotkeyHandler
from sybl.hotkeys.bindings import ParsedBinding, parse_binding

logger = logging.getLogger("sybl.hotkeys.pynput")

_CTRL_KEYS = frozenset(
    {keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r}
)
_SHIFT_KEYS = frozenset(
    {keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r}
)
_ALT_KEYS = frozenset({keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_gr})
_CMD_KEYS = frozenset({keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r})

_SPECIAL_KEY_MAP: dict[str, keyboard.Key] = {
    "space": keyboard.Key.space,
    "enter": keyboard.Key.enter,
    "tab": keyboard.Key.tab,
    "esc": keyboard.Key.esc,
    "backspace": keyboard.Key.backspace,
    "delete": keyboard.Key.delete,
    "insert": keyboard.Key.insert,
    "home": keyboard.Key.home,
    "end": keyboard.Key.end,
    "pageup": keyboard.Key.page_up,
    "pagedown": keyboard.Key.page_down,
    "up": keyboard.Key.up,
    "down": keyboard.Key.down,
    "left": keyboard.Key.left,
    "right": keyboard.Key.right,
    "f1": keyboard.Key.f1,
    "f2": keyboard.Key.f2,
    "f3": keyboard.Key.f3,
    "f4": keyboard.Key.f4,
    "f5": keyboard.Key.f5,
    "f6": keyboard.Key.f6,
    "f7": keyboard.Key.f7,
    "f8": keyboard.Key.f8,
    "f9": keyboard.Key.f9,
    "f10": keyboard.Key.f10,
    "f11": keyboard.Key.f11,
    "f12": keyboard.Key.f12,
}


class PynputHotkeyManager:
    """Push-to-talk hotkeys via pynput keyboard listener."""

    def __init__(self, config: HotkeyConfig) -> None:
        self._config = config
        self._binding = parse_binding(config.binding)
        self._cancel = parse_binding(config.cancel_binding)
        self._handler: HotkeyHandler | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._queue: asyncio.Queue[HotkeyEvent | None] | None = None
        self._consumer_task: asyncio.Task[None] | None = None
        self._listener: keyboard.Listener | None = None
        self._pressed: set[str] = set()
        self._active = False

    async def start(self, handler: HotkeyHandler) -> None:
        if self._listener is not None:
            msg = "Hotkey manager is already running"
            raise RuntimeError(msg)

        self._handler = handler
        self._loop = asyncio.get_running_loop()
        self._queue = asyncio.Queue()
        self._consumer_task = asyncio.create_task(self._consume())
        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()
        logger.info(
            "Hotkey listener started (binding=%s, cancel=%s)",
            self._config.binding,
            self._config.cancel_binding,
        )

    async def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

        if self._queue is not None:
            await self._queue.put(None)

        if self._consumer_task is not None:
            try:
                await asyncio.wait_for(self._consumer_task, timeout=2.0)
            except TimeoutError:
                self._consumer_task.cancel()
                try:
                    await self._consumer_task
                except asyncio.CancelledError:
                    pass
            except asyncio.CancelledError:
                pass
            self._consumer_task = None

        self._handler = None
        self._pressed.clear()
        self._active = False
        logger.info("Hotkey listener stopped")

    async def _consume(self) -> None:
        assert self._queue is not None
        assert self._handler is not None

        while True:
            event = await self._queue.get()
            if event is None:
                break
            try:
                await self._handler(event)
            except Exception:
                logger.exception("Hotkey handler failed for event %s", event.value)

    def _emit(self, event: HotkeyEvent) -> None:
        if self._loop is None or self._queue is None:
            return
        self._loop.call_soon_threadsafe(self._queue.put_nowait, event)

    def _on_press(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        semantic = _semantic_key(key)
        if semantic is None:
            return

        self._pressed.add(semantic)

        if self._active and semantic in self._cancel.token_set:
            self._emit(HotkeyEvent.CANCEL)
            return

        if not self._active and self._binding.token_set.issubset(self._pressed):
            self._active = True
            self._emit(HotkeyEvent.ACTIVATE)

    def _on_release(self, key: keyboard.Key | keyboard.KeyCode) -> None:
        semantic = _semantic_key(key)
        if semantic is None:
            return

        if semantic in self._pressed:
            self._pressed.remove(semantic)

        if self._active and semantic in self._binding.token_set:
            self._active = False
            self._emit(HotkeyEvent.DEACTIVATE)


def _semantic_key(key: keyboard.Key | keyboard.KeyCode) -> str | None:
    if isinstance(key, keyboard.KeyCode):
        if key.char and len(key.char) == 1 and key.char.isprintable():
            return key.char.lower()
        if key.vk is not None:
            for name, special in _SPECIAL_KEY_MAP.items():
                if key == special:
                    return name
        return None

    if key in _CTRL_KEYS:
        return "ctrl"
    if key in _SHIFT_KEYS:
        return "shift"
    if key in _ALT_KEYS:
        return "alt"
    if key in _CMD_KEYS:
        return "cmd"

    for name, special in _SPECIAL_KEY_MAP.items():
        if key == special:
            return name

    return None


def binding_matches(binding: ParsedBinding, pressed: set[str]) -> bool:
    """Return whether all binding tokens are currently pressed."""
    return binding.token_set.issubset(pressed)


def key_to_semantic(key: Any) -> str | None:
    """Convert a pynput key to a semantic token (for tests)."""
    return _semantic_key(key)
