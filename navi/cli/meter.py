"""Shared live audio level meter for CLI commands."""

from __future__ import annotations

import asyncio
import sys

from navi.audio.session import AudioCaptureSession


async def meter_loop(
    session: AudioCaptureSession,
    stop_event: asyncio.Event,
    *,
    bar_width: int = 24,
    sleep_seconds: float = 0.03,
) -> None:
    while not stop_event.is_set():
        level = session.current_level
        dbfs = session.current_dbfs
        filled = min(bar_width, int(level * bar_width))
        bar = "#" * filled + "-" * (bar_width - filled)
        line = f"\rLevel: [{bar}] {dbfs:5.0f} dBFS"
        sys.stdout.write(line)
        sys.stdout.flush()
        await asyncio.sleep(sleep_seconds)


async def wait_for_enter(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sys.stdin.readline)
    stop_event.set()
