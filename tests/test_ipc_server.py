"""Tests for IPC server command handling."""

from __future__ import annotations

import pytest

from navi.ipc.client import IpcClient
from navi.ipc.protocol import CommandName, DaemonInfo
from navi.ipc.server import IpcServer


@pytest.mark.asyncio
async def test_ipc_ping_and_status() -> None:
    async def handler(command: CommandName, params: dict) -> dict:
        if command is CommandName.PING:
            return {"pong": True}
        if command is CommandName.GET_STATUS:
            return {"state": "idle", "provider": "groq"}
        raise ValueError("unknown")

    server = IpcServer(
        host="127.0.0.1",
        command_port=0,
        event_port=0,
        token="test-token",
        command_handler=handler,
    )
    await server.start()
    info = DaemonInfo(
        pid=1,
        host="127.0.0.1",
        command_port=server.command_port,
        event_port=server.event_port,
        token="test-token",
    )
    client = IpcClient(info)
    try:
        assert (await client.ping())["pong"] is True
        status = await client.get_status()
        assert status["state"] == "idle"
    finally:
        await server.stop()
