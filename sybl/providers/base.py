"""STT provider protocol."""

from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterable
from typing import Protocol

from sybl.providers.types import TranscriptionResult


class STTProvider(Protocol):
    name: str

    async def transcribe(
        self,
        audio: bytes | AsyncIterable[bytes],
    ) -> AsyncGenerator[TranscriptionResult, None]: ...
