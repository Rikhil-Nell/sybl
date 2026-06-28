"""Ring buffer of recent transcription results for TUI history."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass(frozen=True)
class TranscriptEntry:
    timestamp: datetime
    raw_text: str
    final_text: str
    provider: str
    model: str | None
    audio_duration_seconds: float
    latency_seconds: float

    def to_dict(self) -> dict[str, object]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "raw_text": self.raw_text,
            "final_text": self.final_text,
            "provider": self.provider,
            "model": self.model,
            "audio_duration_seconds": self.audio_duration_seconds,
            "latency_seconds": self.latency_seconds,
        }


class TranscriptHistory:
    def __init__(self, capacity: int = 100) -> None:
        self._capacity = max(1, capacity)
        self._entries: deque[TranscriptEntry] = deque(maxlen=self._capacity)

    def add(
        self,
        *,
        raw_text: str,
        final_text: str,
        provider: str,
        model: str | None,
        audio_duration_seconds: float,
        latency_seconds: float,
        timestamp: datetime | None = None,
    ) -> TranscriptEntry:
        entry = TranscriptEntry(
            timestamp=timestamp or datetime.now(tz=UTC),
            raw_text=raw_text,
            final_text=final_text,
            provider=provider,
            model=model,
            audio_duration_seconds=audio_duration_seconds,
            latency_seconds=latency_seconds,
        )
        self._entries.append(entry)
        return entry

    def get_recent(self, count: int | None = None) -> list[TranscriptEntry]:
        if count is None:
            return list(self._entries)
        return list(self._entries)[-count:]
