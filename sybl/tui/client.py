"""IPC client wrapper for the Textual TUI."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from sybl.ipc.client import (
    IpcClient,
    IpcConnectionError,
    is_daemon_running,
    load_daemon_info,
)


class TuiIpcClient:
    def __init__(self) -> None:
        self._client: IpcClient | None = None

    @staticmethod
    def ensure_daemon() -> None:
        if not is_daemon_running():
            raise IpcConnectionError(
                "sybl daemon is not running. Start it with `sybl start`."
            )

    async def connect(self) -> None:
        self.ensure_daemon()
        self._client = IpcClient(load_daemon_info())

    @property
    def client(self) -> IpcClient:
        if self._client is None:
            raise IpcConnectionError("Not connected")
        return self._client

    async def get_status(self) -> dict[str, Any]:
        return await self.client.get_status()

    async def get_config(self) -> dict[str, Any]:
        result = await self.client.get_config()
        config = result.get("config", {})
        return dict(config) if isinstance(config, dict) else {}

    async def patch_config(self, patch: dict[str, Any]) -> dict[str, Any]:
        result = await self.client.patch_config(patch)
        config = result.get("config", {})
        return dict(config) if isinstance(config, dict) else {}

    async def list_provider_keys(self) -> list[str]:
        return await self.client.list_provider_keys()

    async def set_provider_key(self, provider: str, key: str) -> None:
        await self.client.set_provider_key(provider, key)

    async def get_logs(self, *, after_cursor: int = 0) -> dict[str, Any]:
        return await self.client.get_logs(after_cursor=after_cursor)

    async def get_history(self) -> list[dict[str, Any]]:
        return await self.client.get_history()

    async def stream_events(self) -> AsyncIterator[dict[str, Any]]:
        async for event in self.client.stream_events():
            yield event

    async def connect_event_reader(self) -> asyncio.StreamReader:
        reader, _writer = await self.client.connect_events()
        return reader
