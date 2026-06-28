"""Tests for TUI IPC client wrapper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from sybl.ipc.client import IpcConnectionError
from sybl.tui.client import TuiIpcClient


def test_ensure_daemon_raises_when_down() -> None:
    with patch("sybl.tui.client.is_daemon_running", return_value=False):
        with pytest.raises(IpcConnectionError):
            TuiIpcClient.ensure_daemon()


@pytest.mark.asyncio
async def test_connect_loads_client() -> None:
    client = TuiIpcClient()
    mock_ipc = AsyncMock()
    mock_ipc.get_status.return_value = {"state": "idle"}
    with (
        patch("sybl.tui.client.is_daemon_running", return_value=True),
        patch("sybl.tui.client.load_daemon_info"),
        patch("sybl.tui.client.IpcClient", return_value=mock_ipc),
    ):
        await client.connect()
        status = await client.get_status()
    assert status["state"] == "idle"
