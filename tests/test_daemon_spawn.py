"""Tests for background daemon spawn helpers."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from sybl.daemon.spawn import (
    _daemon_command,
    spawn_background_daemon,
    wait_for_daemon_ready,
)


def test_daemon_command_includes_foreground() -> None:
    cmd = _daemon_command(verbose=False)
    assert cmd[-2:] == ["start", "--foreground"]
    exe = Path(cmd[0])
    if sys.platform == "win32" and exe.with_name("pythonw.exe").is_file():
        assert exe.name == "pythonw.exe"
    else:
        assert "python" in exe.name.lower()


def test_daemon_command_verbose_flag() -> None:
    cmd = _daemon_command(verbose=True)
    assert "--verbose" in cmd


def test_spawn_background_daemon_detached() -> None:
    with patch("sybl.daemon.spawn.subprocess.Popen") as popen:
        popen.return_value = MagicMock()
        spawn_background_daemon(verbose=False)
    kwargs = popen.call_args.kwargs
    assert kwargs["stdin"] is not None
    assert kwargs["stdout"] is not None
    if sys.platform == "win32":
        assert "creationflags" in kwargs
    else:
        assert kwargs.get("start_new_session") is True


def test_wait_for_daemon_ready_returns_pid() -> None:
    mock_info = MagicMock()
    mock_info.pid = 4242
    mock_client = MagicMock()
    mock_client.info = mock_info
    with (
        patch("sybl.daemon.spawn.is_daemon_running", return_value=True),
        patch("sybl.daemon.spawn.asyncio.run", return_value=True),
        patch("sybl.daemon.spawn.IpcClient", return_value=mock_client),
        patch("sybl.daemon.spawn.time.sleep"),
    ):
        pid = wait_for_daemon_ready(timeout=1.0)
    assert pid == 4242


def test_wait_for_daemon_ready_times_out() -> None:
    with (
        patch("sybl.daemon.spawn.is_daemon_running", return_value=False),
        patch("sybl.daemon.spawn.time.sleep"),
        patch("sybl.daemon.spawn.time.monotonic", side_effect=[0.0, 0.0, 20.0]),
    ):
        with pytest.raises(TimeoutError):
            wait_for_daemon_ready(timeout=1.0)
