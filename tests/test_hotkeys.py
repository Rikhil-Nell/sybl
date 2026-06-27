"""Tests for pynput hotkey backend event detection."""

from __future__ import annotations

import asyncio

import pytest
from pynput import keyboard

from navi.config.models import HotkeyConfig
from navi.hotkeys.base import HotkeyEvent
from navi.hotkeys.pynput_backend import PynputHotkeyManager, key_to_semantic


def test_key_to_semantic_modifiers() -> None:
    assert key_to_semantic(keyboard.Key.ctrl_l) == "ctrl"
    assert key_to_semantic(keyboard.Key.shift) == "shift"
    assert key_to_semantic(keyboard.Key.space) == "space"


@pytest.mark.asyncio
async def test_ptt_press_release_emits_activate_deactivate() -> None:
    config = HotkeyConfig(binding="ctrl+shift+space")
    manager = PynputHotkeyManager(config)
    events: list[HotkeyEvent] = []

    async def handler(event: HotkeyEvent) -> None:
        events.append(event)

    await manager.start(handler)

    manager._on_press(keyboard.Key.ctrl_l)
    manager._on_press(keyboard.Key.shift)
    manager._on_press(keyboard.Key.space)
    await asyncio.sleep(0.05)
    assert events == [HotkeyEvent.ACTIVATE]

    manager._on_release(keyboard.Key.space)
    await asyncio.sleep(0.05)
    assert events == [HotkeyEvent.ACTIVATE, HotkeyEvent.DEACTIVATE]

    await manager.stop()


@pytest.mark.asyncio
async def test_cancel_emits_while_active() -> None:
    config = HotkeyConfig(binding="ctrl+shift+space", cancel_binding="esc")
    manager = PynputHotkeyManager(config)
    events: list[HotkeyEvent] = []

    async def handler(event: HotkeyEvent) -> None:
        events.append(event)

    await manager.start(handler)

    manager._on_press(keyboard.Key.ctrl_l)
    manager._on_press(keyboard.Key.shift)
    manager._on_press(keyboard.Key.space)
    manager._on_press(keyboard.Key.esc)
    await asyncio.sleep(0.05)
    assert HotkeyEvent.CANCEL in events

    await manager.stop()


@pytest.mark.asyncio
async def test_emit_posts_to_async_handler() -> None:
    config = HotkeyConfig(binding="space")
    manager = PynputHotkeyManager(config)
    queue: asyncio.Queue[HotkeyEvent] = asyncio.Queue()

    async def handler(event: HotkeyEvent) -> None:
        await queue.put(event)

    await manager.start(handler)
    manager._on_press(keyboard.Key.space)
    event = await asyncio.wait_for(queue.get(), timeout=1.0)
    assert event is HotkeyEvent.ACTIVATE
    await manager.stop()
