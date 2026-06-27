"""Shared STT provider types."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionResult:
    text: str
    is_final: bool
    confidence: float | None = None
