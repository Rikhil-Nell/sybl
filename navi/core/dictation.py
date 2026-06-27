"""Hotkey-driven dictation orchestration for the daemon."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import replace

from navi.audio import AudioCaptureSession, AudioError
from navi.config.models import NaviConfig
from navi.core.state import SessionState, StateMachine
from navi.core.transcribe import TranscribeOutcome, transcribe_pcm, transcribe_stream
from navi.hotkeys.base import HotkeyEvent
from navi.hotkeys.focus import FocusTarget, capture_foreground
from navi.providers import STTError, resolve_provider
from navi.providers.capabilities import provider_capabilities

logger = logging.getLogger("navi.core.dictation")


class DictationController:
    """Coordinates hotkeys, audio capture, and STT for the daemon."""

    def __init__(self, config: NaviConfig, *, verbose: bool = False) -> None:
        self._config = config
        self._verbose = verbose
        self._state = StateMachine()
        self._session: AudioCaptureSession | None = None
        self._focus: FocusTarget | None = None
        self._stream_task: asyncio.Task[TranscribeOutcome] | None = None
        self._provider_id: str | None = None
        self._provider = None
        self._use_streaming = False
        self._lock = asyncio.Lock()

    @property
    def state(self) -> SessionState:
        return self._state.state

    @property
    def focus_target(self) -> FocusTarget | None:
        return self._focus

    async def handle_hotkey_event(self, event: HotkeyEvent) -> None:
        async with self._lock:
            if event is HotkeyEvent.ACTIVATE:
                await self._on_activate()
            elif event is HotkeyEvent.DEACTIVATE:
                await self._on_deactivate()
            elif event is HotkeyEvent.CANCEL:
                await self._on_cancel()

    async def shutdown(self) -> None:
        async with self._lock:
            await self._cleanup_session(cancel=True)
            if self._state.state is not SessionState.IDLE:
                self._state.reset()

    async def _on_activate(self) -> None:
        if self._state.state is not SessionState.IDLE:
            return

        self._focus = capture_foreground()
        logger.debug(
            "Captured focus target hwnd=%s pid=%s title=%r",
            self._focus.hwnd,
            self._focus.pid,
            self._focus.title,
        )

        streaming_required = self._config.hotkey.streaming == "on"
        self._provider_id, self._provider = resolve_provider(
            self._config,
            streaming_required=streaming_required,
        )
        self._use_streaming = _should_stream(
            self._config,
            self._provider_id,
            streaming_required=streaming_required,
        )

        self._state.transition(SessionState.LISTENING)
        self._session = AudioCaptureSession(self._config.audio)

        try:
            await self._session.start()
        except AudioError:
            self._state.transition(SessionState.ERROR)
            self._state.transition(SessionState.IDLE)
            await self._reset_session()
            raise

        logger.info(
            "Dictation started (provider=%s, streaming=%s)",
            self._provider_id,
            self._use_streaming,
        )

        if self._use_streaming:
            assert self._session is not None
            self._stream_task = asyncio.create_task(
                transcribe_stream(
                    self._config,
                    self._session,
                    provider_id=self._provider_id,
                    provider=self._provider,
                    on_partial=self._on_partial,
                    state=self._state,
                )
            )

    async def _on_deactivate(self) -> None:
        if self._state.state is not SessionState.LISTENING or self._session is None:
            return

        session = self._session
        try:
            pcm = await session.stop()
        except AudioError as exc:
            logger.error("Audio capture failed: %s", exc)
            self._state.transition(SessionState.ERROR)
            self._state.transition(SessionState.IDLE)
            await self._reset_session()
            return

        stats = session.stats()
        min_duration = self._config.hotkey.min_duration_ms / 1000.0
        if stats.duration_seconds < min_duration:
            logger.debug(
                "Capture too short (%.2fs), skipping STT",
                stats.duration_seconds,
            )
            if self._stream_task is not None:
                self._stream_task.cancel()
                try:
                    await self._stream_task
                except asyncio.CancelledError:
                    pass
            self._state.transition(SessionState.IDLE)
            await self._reset_session()
            return

        self._state.transition(SessionState.PROCESSING)

        try:
            if self._use_streaming and self._stream_task is not None:
                stream_exc = self._stream_task.exception()
                if self._stream_task.done() and stream_exc is not None:
                    await self._stream_task
                outcome = await self._stream_task
                outcome = replace(
                    outcome,
                    audio_duration_seconds=stats.duration_seconds,
                    peak_dbfs=stats.peak_dbfs,
                )
            else:
                outcome = await transcribe_pcm(
                    self._config,
                    pcm,
                    provider_name=self._provider_id,
                    audio_duration_seconds=stats.duration_seconds,
                    peak_dbfs=stats.peak_dbfs,
                    state=self._state,
                )
        except STTError as exc:
            logger.error("Transcription failed: %s", exc)
            if self._state.state is SessionState.PROCESSING:
                self._state.transition(SessionState.ERROR)
                self._state.transition(SessionState.IDLE)
            await self._reset_session()
            return

        self._log_outcome(outcome)
        if self._state.state is not SessionState.IDLE:
            self._state.reset()
        await self._reset_session()

    async def _on_cancel(self) -> None:
        if self._state.state is not SessionState.LISTENING:
            return

        logger.info("Dictation cancelled")
        await self._cleanup_session(cancel=True)
        self._state.transition(SessionState.CANCELLED)
        self._state.transition(SessionState.IDLE)

    async def _cleanup_session(self, *, cancel: bool) -> None:
        if self._stream_task is not None:
            if not self._stream_task.done():
                self._stream_task.cancel()
            try:
                await self._stream_task
            except asyncio.CancelledError:
                pass
            except STTError:
                pass
            self._stream_task = None

        if self._session is not None:
            if cancel:
                await self._session.cancel()
            self._session = None

        self._provider_id = None
        self._provider = None
        self._use_streaming = False

    async def _reset_session(self) -> None:
        self._stream_task = None
        self._session = None
        self._provider_id = None
        self._provider = None
        self._use_streaming = False

    def _on_partial(self, text: str) -> None:
        if self._verbose:
            logger.info("Partial: %s", text)
        else:
            logger.debug("Partial: %s", text)

    def _log_outcome(self, outcome: TranscribeOutcome) -> None:
        logger.info(
            "Transcript (%s, %.2fs audio, %.2fs latency): %s",
            outcome.provider,
            outcome.audio_duration_seconds,
            outcome.latency_seconds,
            outcome.text or "(empty)",
        )


def _should_stream(
    config: NaviConfig,
    provider_id: str,
    *,
    streaming_required: bool,
) -> bool:
    mode = config.hotkey.streaming
    if mode == "on":
        return True
    if mode == "off":
        return False
    if streaming_required:
        return True
    return provider_capabilities(provider_id).streaming
