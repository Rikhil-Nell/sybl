"""In-process fake IPC client that drives the TUI without a daemon.

Used by ``sybl tui --demo`` to showcase the dashboard (and capture
screenshots) by scripting a realistic dictation cycle:
idle → listening (RMS meter) → processing → inject → idle, on a loop.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from sybl.config import ConfigManager

_SAMPLE_TRANSCRIPTS = [
    "Meeting notes for the v0.1.2 TUI overhaul.",
    "Push back on scope creep and keep the core loop small.",
    "Free dictation with your own speech-to-text key.",
    "Bring your own key, local first, no telemetry.",
    "Ship the mission control dashboard today.",
]


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class DemoIpcClient:
    """Duck-typed stand-in for ``TuiIpcClient`` with scripted events."""

    def __init__(self) -> None:
        self._started = time.monotonic()
        self.state = "idle"
        self._log_cursor = 0
        self.logs: list[dict[str, Any]] = [
            self._log("INFO", "sybl daemon started (demo mode)"),
            self._log(
                "INFO",
                "Hotkey listener active (mode=both, binding=ctrl+alt+space)",
            ),
        ]
        self.history: list[dict[str, Any]] = [
            {
                "final_text": "Hello, this is sybl running in demo mode.",
                "provider": "deepgram",
                "audio_duration_seconds": 2.1,
                "latency_seconds": 0.42,
            },
        ]

    def _log(self, level: str, message: str) -> dict[str, Any]:
        self._log_cursor += 1
        return {"level": level, "message": message, "timestamp": _now()}

    async def connect(self) -> None:
        return None

    async def get_status(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "provider": "deepgram",
            "hotkey_binding": "ctrl+alt+space",
            "hotkey_mode": "both",
            "audio_device": "Demo Microphone",
            "version": "0.1.2",
            "uptime_seconds": time.monotonic() - self._started,
        }

    async def get_config(self) -> dict[str, Any]:
        data = ConfigManager().load().model_dump(mode="json")
        ui = data.setdefault("ui", {})
        if not ui.get("onboarding_complete"):
            ui["onboarding_complete"] = True
        return data

    async def patch_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        return await self.get_config()

    async def list_provider_keys(self) -> list[str]:
        return ["deepgram"]

    async def set_provider_key(self, provider: str, key: str) -> None:
        return None

    async def get_logs(self, *, after_cursor: int = 0) -> dict[str, Any]:
        return {"entries": list(self.logs), "cursor": self._log_cursor}

    async def get_history(self) -> list[dict[str, Any]]:
        return list(self.history)

    async def list_sounds(self) -> dict[str, Any]:
        return {"sounds_dir": "", "files": [], "start_file": None, "stop_file": None}

    async def import_sound(self, role: str, path: str) -> dict[str, Any]:
        return await self.list_sounds()

    async def clear_sound(self, role: str) -> dict[str, Any]:
        return await self.list_sounds()

    async def stream_events(self) -> AsyncIterator[dict[str, Any]]:
        index = 0
        while True:
            self.state = "idle"
            yield {"type": "state_changed", "state": "idle"}
            await asyncio.sleep(2.2)

            self.state = "listening"
            yield {"type": "state_changed", "state": "listening"}
            rec_log = self._log("INFO", "Recording started (Demo Microphone)")
            self.logs.append(rec_log)
            yield {"type": "log_entry", "entry": rec_log, "cursor": self._log_cursor}
            for _ in range(22):
                yield {"type": "level", "value": random.uniform(0.25, 0.95)}
                await asyncio.sleep(0.12)
            yield {"type": "level", "value": 0.0}

            self.state = "processing"
            yield {"type": "state_changed", "state": "processing"}
            await asyncio.sleep(0.8)

            text = _SAMPLE_TRANSCRIPTS[index % len(_SAMPLE_TRANSCRIPTS)]
            index += 1
            entry = {
                "final_text": text,
                "provider": "deepgram",
                "audio_duration_seconds": round(random.uniform(0.9, 3.4), 1),
                "latency_seconds": round(random.uniform(0.3, 0.6), 2),
            }
            self.history.append(entry)
            log = self._log(
                "INFO",
                f"Transcript (deepgram, {entry['audio_duration_seconds']}s audio, "
                f"{entry['latency_seconds']}s latency)",
            )
            self.logs.append(log)
            yield {"type": "transcript", "entry": entry}
            yield {"type": "log_entry", "entry": log, "cursor": self._log_cursor}

            self.state = "injecting"
            yield {"type": "state_changed", "state": "injecting"}
            inject_log = self._log("INFO", "Injected transcript into focused app")
            self.logs.append(inject_log)
            yield {"type": "log_entry", "entry": inject_log, "cursor": self._log_cursor}
            await asyncio.sleep(1.0)
