"""Navi daemon — owns dictation, config, IPC, and event fan-out."""

from __future__ import annotations

import asyncio
import logging
import secrets
import signal
import time
from typing import Any

from navi import __version__
from navi.config.manager import ConfigManager
from navi.config.models import NaviConfig
from navi.config.paths import log_path
from navi.core.dictation import DictationController
from navi.core.events import EventBus
from navi.core.history import TranscriptHistory
from navi.core.state import SessionState
from navi.core.transcribe import TranscribeOutcome
from navi.hotkeys import create_hotkey_manager
from navi.indicator import create_indicator
from navi.ipc.protocol import CommandName, DaemonInfo
from navi.ipc.server import IpcServer
from navi.ipc.single_instance import DaemonLock
from navi.logging import setup_logging
from navi.logging.ring_buffer import LogEntry
from navi.secrets import list_configured_providers, set_provider_key

logger = logging.getLogger("navi.core.daemon")


class NaviDaemon:
    def __init__(
        self,
        *,
        config_manager: ConfigManager | None = None,
        verbose: bool = False,
        lock: DaemonLock | None = None,
    ) -> None:
        self._config_manager = config_manager or ConfigManager()
        self._verbose = verbose
        self._lock = lock or DaemonLock.default()
        self._config = self._config_manager.load()
        self._ring_handler = setup_logging(
            self._config.logging,
            log_file=log_path(),
            verbose=verbose,
        )
        self._history = TranscriptHistory(self._config.ipc.history_size)
        self._events = EventBus(log_history_size=self._config.logging.ring_buffer_size)
        self._started_at = time.monotonic()
        self._shutdown_event = asyncio.Event()
        self._level_task: asyncio.Task[None] | None = None
        self._ipc: IpcServer | None = None
        self._token = secrets.token_urlsafe(32)
        self._controller = DictationController(
            self._config,
            verbose=verbose,
            on_state_changed=self._on_state_changed,
            on_transcript=self._on_transcript,
        )
        self._hotkeys = create_hotkey_manager(self._config.hotkey)
        self._indicator = create_indicator(self._config)
        self._wire_log_handler()

    @property
    def config(self) -> NaviConfig:
        return self._config

    @property
    def daemon_info(self) -> DaemonInfo | None:
        if self._ipc is None:
            return None
        return DaemonInfo(
            pid=__import__("os").getpid(),
            host=self._config.ipc.host,
            command_port=self._ipc.command_port,
            event_port=self._ipc.event_port,
            token=self._token,
        )

    def _wire_log_handler(self) -> None:
        original_emit = self._ring_handler.emit

        def emit_with_events(record: logging.LogRecord) -> None:
            original_emit(record)
            entries = self._ring_handler.get_recent(1)
            if not entries:
                return
            entry = entries[-1]
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                return
            loop.create_task(self._events.emit_log_entry(entry))

        self._ring_handler.emit = emit_with_events  # type: ignore[method-assign]

    async def _on_state_changed(self, state: SessionState) -> None:
        await self._events.emit_state_changed(state)
        if state is SessionState.LISTENING:
            self._indicator.show()
            if self._level_task is None or self._level_task.done():
                self._level_task = asyncio.create_task(self._poll_levels())
        else:
            self._indicator.hide()
            if self._level_task is not None and not self._level_task.done():
                self._level_task.cancel()

    async def _on_transcript(
        self,
        outcome: TranscribeOutcome,
        raw_text: str,
        final_text: str,
    ) -> None:
        if not final_text.strip() and not raw_text.strip():
            return
        entry = self._history.add(
            raw_text=raw_text,
            final_text=final_text,
            provider=outcome.provider,
            model=outcome.model,
            audio_duration_seconds=outcome.audio_duration_seconds,
            latency_seconds=outcome.latency_seconds,
        )
        await self._events.emit_transcript(entry)

    async def _poll_levels(self) -> None:
        try:
            while self._controller.state is SessionState.LISTENING:
                level = self._controller.current_level
                self._indicator.update_level(level)
                await self._events.emit_level(level)
                await asyncio.sleep(0.05)
        except asyncio.CancelledError:
            pass

    async def _event_bridge(self, payload: dict[str, Any]) -> None:
        if self._ipc is not None:
            await self._ipc.broadcast_event(payload)

    async def _handle_command(
        self,
        command: CommandName,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        if command is CommandName.PING:
            return {"pong": True}

        if command is CommandName.GET_STATUS:
            return {
                "state": self._controller.state.value,
                "provider": self._config.provider.preferred,
                "hotkey_binding": self._config.hotkey.binding,
                "hotkey_mode": self._config.hotkey.mode,
                "audio_device": self._config.audio.device or "default",
                "version": __version__,
                "uptime_seconds": time.monotonic() - self._started_at,
            }

        if command is CommandName.GET_CONFIG:
            return {"config": self._config.model_dump(mode="json")}

        if command is CommandName.PATCH_CONFIG:
            patch = params.get("patch", {})
            if not isinstance(patch, dict):
                raise ValueError("patch must be an object")
            await self.apply_config(patch)
            return {"config": self._config.model_dump(mode="json")}

        if command is CommandName.LIST_PROVIDER_KEYS:
            return {"providers": list_configured_providers()}

        if command is CommandName.SET_PROVIDER_KEY:
            provider = str(params.get("provider", ""))
            key = str(params.get("key", ""))
            if not provider or not key:
                raise ValueError("provider and key are required")
            set_provider_key(provider, key)
            return {"provider": provider}

        if command is CommandName.GET_LOGS:
            after_cursor = int(params.get("after_cursor", 0))
            entries, cursor = self._events.get_logs_since(after_cursor)
            if after_cursor <= 0:
                entries = self._ring_handler.get_recent()
                cursor = self._events.log_cursor
            return {
                "entries": [_log_entry_dict(e) for e in entries],
                "cursor": cursor,
            }

        if command is CommandName.GET_HISTORY:
            count = params.get("count")
            if count is None:
                entries = self._history.get_recent()
            else:
                entries = self._history.get_recent(int(count))
            return {"entries": [e.to_dict() for e in entries]}

        if command is CommandName.SHUTDOWN:
            self._shutdown_event.set()
            return {"stopping": True}

        raise ValueError(f"Unknown command: {command}")

    async def apply_config(self, patch: dict[str, Any]) -> None:
        merged = self._config.model_dump(mode="python")
        _deep_merge(merged, patch)
        new_config = NaviConfig.model_validate(merged)
        hotkey_changed = new_config.hotkey != self._config.hotkey
        indicator_changed = new_config.indicator != self._config.indicator
        self._config = new_config
        self._config_manager.save(new_config)
        self._controller.update_config(new_config)
        if indicator_changed:
            self._indicator.shutdown()
            self._indicator = create_indicator(new_config)
        if hotkey_changed:
            await self._hotkeys.stop()
            self._hotkeys = create_hotkey_manager(new_config.hotkey)
            await self._hotkeys.start(self._controller.handle_hotkey_event)
        await self._events.emit_config_changed()

    async def run(self) -> None:
        self._lock.acquire()
        host = self._config.ipc.host
        self._ipc = IpcServer(
            host=host,
            command_port=self._config.ipc.command_port or 0,
            event_port=self._config.ipc.event_port or 0,
            token=self._token,
            command_handler=self._handle_command,
        )
        await self._ipc.start()
        info = self.daemon_info
        if info is not None:
            self._lock.write_info(info)
            print(
                f"IPC: command port {info.command_port}, "
                f"event port {info.event_port}",
                flush=True,
            )

        self._events.subscribe(self._event_bridge)

        loop = asyncio.get_running_loop()

        def _request_stop() -> None:
            logger.info("Shutdown requested")
            self._shutdown_event.set()

        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _request_stop)
            except NotImplementedError:
                signal.signal(sig, lambda _s, _f: _request_stop())

        await self._hotkeys.start(self._controller.handle_hotkey_event)
        logger.info("Navi daemon started")

        try:
            await self._shutdown_event.wait()
        finally:
            await self.shutdown()

    async def shutdown(self) -> None:
        if self._level_task is not None and not self._level_task.done():
            self._level_task.cancel()
        await self._controller.shutdown()
        await self._hotkeys.stop()
        self._indicator.hide()
        self._indicator.shutdown()
        if self._ipc is not None:
            await self._ipc.stop()
            self._ipc = None
        self._lock.release()
        logger.info("Navi daemon stopped")


def _log_entry_dict(entry: LogEntry) -> dict[str, str]:
    return {
        "timestamp": entry.timestamp.isoformat(),
        "level": entry.level,
        "logger": entry.logger,
        "message": entry.message,
    }


def _deep_merge(base: dict[str, Any], patch: dict[str, Any]) -> None:
    for key, value in patch.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(value, dict)
        ):
            _deep_merge(base[key], value)
        else:
            base[key] = value


async def run_daemon(*, verbose: bool = False) -> None:
    daemon = NaviDaemon(verbose=verbose)
    await daemon.run()
