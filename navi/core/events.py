"""In-process event bus for daemon IPC fan-out."""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from navi.core.history import TranscriptEntry
from navi.core.state import SessionState
from navi.logging.ring_buffer import LogEntry

logger = logging.getLogger("navi.core.events")

EventHandler = Callable[[dict[str, Any]], Awaitable[None] | None]


@dataclass(frozen=True)
class DaemonEvent:
    type: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, **self.payload}


class EventBus:
    def __init__(self, *, log_history_size: int = 500) -> None:
        self._handlers: list[EventHandler] = []
        self._log_cursor = 0
        self._log_history: deque[tuple[int, LogEntry]] = deque(maxlen=log_history_size)

    @property
    def log_cursor(self) -> int:
        return self._log_cursor

    def subscribe(self, handler: EventHandler) -> Callable[[], None]:
        self._handlers.append(handler)

        def unsubscribe() -> None:
            if handler in self._handlers:
                self._handlers.remove(handler)

        return unsubscribe

    async def publish(self, event: DaemonEvent) -> None:
        payload = event.to_dict()
        for handler in list(self._handlers):
            try:
                result = handler(payload)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                logger.exception("Event handler failed for %s", event.type)

    async def emit_state_changed(self, state: SessionState) -> None:
        await self.publish(DaemonEvent("state_changed", {"state": state.value}))

    async def emit_transcript(self, entry: TranscriptEntry) -> None:
        await self.publish(
            DaemonEvent("transcript", {"entry": entry.to_dict()}),
        )

    async def emit_log_entry(self, entry: LogEntry) -> None:
        self._log_cursor += 1
        self._log_history.append((self._log_cursor, entry))
        await self.publish(
            DaemonEvent(
                "log_entry",
                {
                    "entry": {
                        "timestamp": entry.timestamp.isoformat(),
                        "level": entry.level,
                        "logger": entry.logger,
                        "message": entry.message,
                    },
                    "cursor": self._log_cursor,
                },
            ),
        )

    def get_logs_since(self, after_cursor: int) -> tuple[list[LogEntry], int]:
        entries = [
            entry for cursor, entry in self._log_history if cursor > after_cursor
        ]
        return entries, self._log_cursor

    async def emit_level(self, value: float) -> None:
        await self.publish(DaemonEvent("level", {"value": value}))

    async def emit_config_changed(self) -> None:
        await self.publish(DaemonEvent("config_changed", {}))
