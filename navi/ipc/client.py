"""Async IPC client for daemon command and event channels."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from navi.config.paths import state_dir
from navi.ipc.process import is_pid_alive
from navi.ipc.protocol import (
    CommandName,
    CommandRequest,
    CommandResponse,
    DaemonInfo,
    decode_line,
    encode_line,
)


class IpcConnectionError(Exception):
    """Raised when the daemon is unreachable or returns an error."""


def daemon_info_path() -> Path:
    return state_dir() / "daemon.json"


def load_daemon_info(path: Path | None = None) -> DaemonInfo | None:
    info_path = path or daemon_info_path()
    if not info_path.exists():
        return None
    try:
        data = json.loads(info_path.read_text(encoding="utf-8"))
        return DaemonInfo.model_validate(data)
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def is_daemon_running(path: Path | None = None) -> bool:
    info = load_daemon_info(path)
    if info is None:
        return False
    return is_pid_alive(info.pid)


class IpcClient:
    def __init__(self, info: DaemonInfo | None = None) -> None:
        self._info = info or load_daemon_info()
        if self._info is None:
            raise IpcConnectionError(
                "Navi daemon is not running. Start it with `navi start`."
            )

    @property
    def info(self) -> DaemonInfo:
        assert self._info is not None
        return self._info

    async def command(
        self,
        name: CommandName,
        params: dict[str, Any] | None = None,
        *,
        timeout: float = 10.0,
    ) -> dict[str, Any]:
        request_id = uuid.uuid4().hex
        payload = CommandRequest(
            id=request_id,
            command=name,
            params=params or {},
        )
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(self.info.host, self.info.command_port),
            timeout=timeout,
        )
        try:
            writer.write(encode_line(payload.model_dump(mode="json")))
            await writer.drain()
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if not line:
                raise IpcConnectionError("Daemon closed command connection")
            response = CommandResponse.model_validate(decode_line(line))
            if response.id != request_id:
                raise IpcConnectionError("Mismatched response id")
            if not response.ok:
                raise IpcConnectionError(response.error or "Command failed")
            return response.result or {}
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def ping(self) -> dict[str, Any]:
        return await self.command(CommandName.PING)

    async def get_status(self) -> dict[str, Any]:
        return await self.command(CommandName.GET_STATUS)

    async def get_config(self) -> dict[str, Any]:
        return await self.command(CommandName.GET_CONFIG)

    async def patch_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        return await self.command(CommandName.PATCH_CONFIG, {"patch": patch})

    async def list_provider_keys(self) -> list[str]:
        result = await self.command(CommandName.LIST_PROVIDER_KEYS)
        keys = result.get("providers", [])
        return list(keys) if isinstance(keys, list) else []

    async def set_provider_key(self, provider: str, key: str) -> None:
        await self.command(
            CommandName.SET_PROVIDER_KEY,
            {"provider": provider, "key": key},
        )

    async def get_logs(self, *, after_cursor: int = 0) -> dict[str, Any]:
        return await self.command(
            CommandName.GET_LOGS,
            {"after_cursor": after_cursor},
        )

    async def get_history(self, count: int | None = None) -> list[dict[str, Any]]:
        params: dict[str, Any] = {}
        if count is not None:
            params["count"] = count
        result = await self.command(CommandName.GET_HISTORY, params)
        entries = result.get("entries", [])
        return list(entries) if isinstance(entries, list) else []

    async def shutdown(self) -> None:
        await self.command(CommandName.SHUTDOWN)

    async def stream_events(self) -> AsyncIterator[dict[str, Any]]:
        reader, writer = await asyncio.open_connection(
            self.info.host,
            self.info.event_port,
        )
        hello = {"type": "hello", "token": self.info.token}
        writer.write(encode_line(hello))
        await writer.drain()
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                yield decode_line(line)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def connect_events(self) -> tuple[asyncio.StreamReader, asyncio.StreamWriter]:
        reader, writer = await asyncio.open_connection(
            self.info.host,
            self.info.event_port,
        )
        writer.write(
            encode_line({"type": "hello", "token": self.info.token}),
        )
        await writer.drain()
        ack = await reader.readline()
        if not ack:
            raise IpcConnectionError("Daemon closed event connection")
        payload = decode_line(ack)
        if payload.get("type") != "subscribed":
            raise IpcConnectionError("Event subscription rejected")
        return reader, writer
