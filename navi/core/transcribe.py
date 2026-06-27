"""End-to-end transcribe pipeline: capture audio then STT."""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterable, Callable
from dataclasses import dataclass

from navi.audio.session import AudioCaptureSession
from navi.config.models import NaviConfig
from navi.core.state import SessionState, StateMachine
from navi.providers import STTError
from navi.providers.base import STTProvider
from navi.providers.manager import resolve_provider
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
    state: StateMachine | None = None,
    manage_idle_transition: bool | None = None,
) -> TranscribeOutcome:
    """Send captured PCM to the configured STT provider."""
    owns_state = state is None
    sm = state or StateMachine()
    if owns_state:
        sm.transition(SessionState.LISTENING)
        sm.transition(SessionState.PROCESSING)

    if manage_idle_transition is None:
        manage_idle_transition = owns_state

    provider_id, provider = resolve_provider(
        config,
        prefer=provider_name,
        streaming_required=False,
    )

    model = _provider_model(config, provider_id)
    start = time.monotonic()

    try:
        text = await _collect_final_text(provider.transcribe(pcm))
    except STTError:
        if sm.state == SessionState.PROCESSING:
            sm.transition(SessionState.ERROR)
        raise

    latency = time.monotonic() - start
    if manage_idle_transition and sm.state == SessionState.PROCESSING:
        sm.transition(SessionState.IDLE)

    return TranscribeOutcome(
        text=text,
        provider=provider_id,
        model=model,
        audio_duration_seconds=audio_duration_seconds,
        latency_seconds=latency,
        peak_dbfs=peak_dbfs,
    )


async def transcribe_stream(
    config: NaviConfig,
    session: AudioCaptureSession,
    *,
    provider_name: str | None = None,
    provider_id: str | None = None,
    provider: STTProvider | None = None,
    on_partial: Callable[[str], None] | None = None,
    audio_duration_seconds: float = 0.0,
    peak_dbfs: float = 0.0,
    state: StateMachine | None = None,
    manage_idle_transition: bool | None = None,
) -> TranscribeOutcome:
    """Stream PCM chunks from an active session to a streaming STT provider."""
    owns_state = state is None
    sm = state or StateMachine()
    if owns_state:
        sm.transition(SessionState.LISTENING)
        sm.transition(SessionState.PROCESSING)

    if manage_idle_transition is None:
        manage_idle_transition = owns_state

    if provider is None or provider_id is None:
        provider_id, provider = resolve_provider(
            config,
            prefer=provider_name,
            streaming_required=True,
        )

    model = _provider_model(config, provider_id)
    start = time.monotonic()

    async def pcm_chunks() -> AsyncIterable[bytes]:
        async for chunk in session.chunks():
            yield chunk.pcm

    try:
        text = await _collect_stream_text(
            provider.transcribe(pcm_chunks()),
            on_partial=on_partial,
        )
    except STTError:
        if sm.state in {SessionState.LISTENING, SessionState.PROCESSING}:
            sm.transition(SessionState.ERROR)
        raise

    latency = time.monotonic() - start
    if manage_idle_transition and sm.state == SessionState.PROCESSING:
        sm.transition(SessionState.IDLE)

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
    if provider_id == "deepgram":
        return config.provider.deepgram.model
    return None


async def _collect_final_text(results) -> str:
    final_parts: list[str] = []
    async for result in results:
        assert isinstance(result, TranscriptionResult)
        if result.is_final:
            final_parts.append(result.text)
    return "".join(final_parts).strip()


async def _collect_stream_text(
    results,
    *,
    on_partial: Callable[[str], None] | None = None,
) -> str:
    latest_final = ""
    latest_partial = ""
    async for result in results:
        assert isinstance(result, TranscriptionResult)
        if result.is_final:
            latest_final = result.text
            if on_partial is not None:
                on_partial(result.text)
        else:
            latest_partial = result.text
            if on_partial is not None:
                on_partial(result.text)
    return (latest_final or latest_partial).strip()
