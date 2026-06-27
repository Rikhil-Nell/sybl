"""In-memory ring buffer for recent log records."""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class LogEntry:
    timestamp: datetime
    level: str
    logger: str
    message: str


class RingBufferHandler(logging.Handler):
    def __init__(self, capacity: int) -> None:
        super().__init__()
        self._entries: deque[LogEntry] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        entry = LogEntry(
            timestamp=datetime.fromtimestamp(record.created),
            level=record.levelname,
            logger=record.name,
            message=record.getMessage(),
        )
        self._entries.append(entry)

    def get_recent(self, count: int | None = None) -> list[LogEntry]:
        if count is None:
            return list(self._entries)
        return list(self._entries)[-count:]
