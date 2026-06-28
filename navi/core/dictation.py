"""Hotkey-driven dictation orchestration for the daemon."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import replace

from navi.audio import AudioCaptureSession, AudioError
from navi.config.models import NaviConfig
from navi.config.vocabulary import VocabularyStore
from navi.core.postprocess import process_text
from navi.core.state import SessionState, StateMachine
from navi.core.transcribe import TranscribeOutcome, transcribe_pcm, transcribe_stream
from navi.core.voice_commands import apply_voice_commands
from navi.hotkeys.base import HotkeyEvent
from navi.hotkeys.focus import FocusTarget, capture_foreground
from navi.inject import InjectError, TextInjector, create_injector
from navi.providers import STTError, resolve_provider
from navi.providers.capabilities import provider_capabilities

logger = logging.getLogger("navi.core.dictation")

StateChangedCallback = Callable[[SessionState], Awaitable[None] | None]
TranscriptCallback = Callable[
    [TranscribeOutcome, str, str],
    Awaitable[None] | None,
]


class DictationController:
    """Coordinates hotkeys, audio capture, STT, and text injection for the daemon."""

    def __init__(
        self,
        config: NaviConfig,
        *,
        verbose: bool = False,
        injector: TextInjector | None = None,
        on_state_changed: StateChangedCallback | None = None,
        on_transcript: TranscriptCallback | None = None,
    ) -> None:
        self._config = config
        self._verbose = verbose
        self._state = StateMachine()
        self._session: AudioCaptureSession | None = None
        self._focus: FocusTarget | None = None
        self._stream_task: asyncio.Task[TranscribeOutcome] | None = None
        self._provider_id: str | None = None
        self._provider = None
        self._use_streaming = False
        self._injector = injector or create_injector(config)
        self._lock = asyncio.Lock()
        self._on_state_changed = on_state_changed
        self._on_transcript = on_transcript

    @property
    def state(self) -> SessionState:
        return self._state.state

    @property
    def focus_target(self) -> FocusTarget | None:
        return self._focus

    @property
    def current_level(self) -> float:
        if self._session is None:
            return 0.0
        return self._session.current_level

    def update_config(self, config: NaviConfig) -> None:
        self._config = config
        self._injector = create_injector(config)

    async def _transition(self, to: SessionState) -> None:
        self._state.transition(to)
        if self._on_state_changed is not None:
            result = self._on_state_changed(to)
            if asyncio.iscoroutine(result):
                await result

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
        vocabulary = self._load_vocabulary_terms()
        self._provider_id, self._provider = resolve_provider(
            self._config,
            streaming_required=streaming_required,
            vocabulary=vocabulary,
        )
        self._use_streaming = _should_stream(
            self._config,
            self._provider_id,
            streaming_required=streaming_required,
        )

        await self._transition(SessionState.LISTENING)
        self._session = AudioCaptureSession(self._config.audio)

        try:
            await self._session.start()
        except AudioError:
            await self._transition(SessionState.ERROR)
            await self._transition(SessionState.IDLE)
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
                    manage_idle_transition=False,
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
            await self._transition(SessionState.ERROR)
            await self._transition(SessionState.IDLE)
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
            await self._transition(SessionState.IDLE)
            await self._reset_session()
            return

        await self._transition(SessionState.PROCESSING)

        try:
            if self._use_streaming and self._stream_task is not None:
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
                    manage_idle_transition=False,
                )
        except STTError as exc:
            logger.error("Transcription failed: %s", exc)
            if self._state.state is SessionState.PROCESSING:
                await self._transition(SessionState.ERROR)
                await self._transition(SessionState.IDLE)
            await self._reset_session()
            return

        self._log_outcome(outcome)
        await self._finish_outcome(outcome)

    async def _finish_outcome(self, outcome: TranscribeOutcome) -> None:
        final_text = process_text(self._config.postprocess, outcome.text)
        if (
            self._config.postprocess.enabled
            and final_text != outcome.text
        ):
            logger.debug(
                "Post-processed transcript: %r -> %r",
                outcome.text,
                final_text,
            )

        command_result = apply_voice_commands(self._config.voice_commands, final_text)
        final_text = command_result.text
        if command_result.skip_inject:
            logger.info("Voice command cancelled injection for this utterance")

        if self._on_transcript is not None:
            result = self._on_transcript(outcome, outcome.text, final_text)
            if asyncio.iscoroutine(result):
                await result

        try:
            if command_result.skip_inject:
                await self._transition(SessionState.IDLE)
            elif final_text.strip() and self._config.inject.enabled:
                await self._transition(SessionState.INJECTING)
                try:
                    await asyncio.wait_for(
                        self._injector.inject(final_text, self._focus),
                        timeout=15.0,
                    )
                except TimeoutError as exc:
                    raise InjectError("Injection timed out after 15s") from exc
                logger.info("Injected transcript into focused application")
            elif final_text.strip():
                logger.info(
                    "Final transcript: %s",
                    final_text,
                )
            await self._transition(SessionState.IDLE)
        except InjectError as exc:
            logger.error("Injection failed: %s", exc)
            if self._state.state is SessionState.INJECTING:
                await self._transition(SessionState.ERROR)
            elif self._state.state is SessionState.PROCESSING:
                await self._transition(SessionState.ERROR)
            await self._transition(SessionState.IDLE)
        except Exception:
            logger.exception("Injection failed unexpectedly")
            if self._state.state is SessionState.INJECTING:
                await self._transition(SessionState.ERROR)
            elif self._state.state is SessionState.PROCESSING:
                await self._transition(SessionState.ERROR)
            if self._state.state is not SessionState.IDLE:
                await self._transition(SessionState.IDLE)
        await self._reset_session()

    async def _on_cancel(self) -> None:
        if self._state.state is not SessionState.LISTENING:
            return

        logger.info("Dictation cancelled")
        await self._cleanup_session(cancel=True)
        await self._transition(SessionState.CANCELLED)
        await self._transition(SessionState.IDLE)

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

    def _load_vocabulary_terms(self) -> list[str]:
        if not self._config.vocabulary.enabled:
            return []
        return VocabularyStore().load_terms()


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
