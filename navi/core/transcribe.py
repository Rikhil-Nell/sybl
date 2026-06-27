"""End-to-end transcribe pipeline: capture audio then STT."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from navi.config.models import NaviConfig
from navi.core.state import SessionState, StateMachine
from navi.providers import STTError, get_provider
from navi.providers.types import TranscriptionResult

logger = logging.getLogger("navi.core.transcribe")


@dataclass(frozen=True)
class TranscribeOutcome:
    text: str
    provider: str
    model: str | None
    audio_duration_seconds: float
    latency_seconds: float
    peak_dbfs: float


async def transcribe_pcm(
    config: NaviConfig,
    pcm: bytes,
    *,
    provider_name: str | None = None,
    audio_duration_seconds: float = 0.0,
    peak_dbfs: float = 0.0,
) -> TranscribeOutcome:
    """Send captured PCM to the configured STT provider."""
    provider_id = provider_name or config.provider.preferred
    state = StateMachine()
    state.transition(SessionState.LISTENING)
    state.transition(SessionState.PROCESSING)

    provider = get_provider(provider_id, config)
    model = _provider_model(config, provider_id)
    start = time.monotonic()

    try:
        text = await _collect_final_text(provider.transcribe(pcm))
    except STTError:
        state.transition(SessionState.ERROR)
        raise

    latency = time.monotonic() - start
    state.transition(SessionState.IDLE)

    return TranscribeOutcome(
        text=text,
        provider=provider_id,
        model=model,
        audio_duration_seconds=audio_duration_seconds,
        latency_seconds=latency,
        peak_dbfs=peak_dbfs,
    )


def _provider_model(config: NaviConfig, provider_id: str) -> str | None:
    if provider_id == "groq":
        return config.provider.groq.model
    return None


async def _collect_final_text(results) -> str:
    final_parts: list[str] = []
    async for result in results:
        assert isinstance(result, TranscriptionResult)
        if result.is_final:
            final_parts.append(result.text)
    return "".join(final_parts).strip()
