"""Spawn sybl daemon as a detached background process."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import time
from pathlib import Path

from sybl.ipc.client import IpcClient, IpcConnectionError, is_daemon_running

if sys.platform == "win32":
    _DETACHED_FLAGS = (
        subprocess.DETACHED_PROCESS
        | subprocess.CREATE_NEW_PROCESS_GROUP
        | subprocess.CREATE_NO_WINDOW
    )
else:
    _DETACHED_FLAGS = 0


def _background_python() -> str:
    """Use pythonw on Windows so no console window is allocated."""
    if sys.platform == "win32":
        pythonw = Path(sys.executable).with_name("pythonw.exe")
        if pythonw.is_file():
            return str(pythonw)
    return sys.executable


def _daemon_command(*, verbose: bool) -> list[str]:
    cmd = [_background_python(), "-m", "sybl"]
    if verbose:
        cmd.append("--verbose")
    cmd.extend(["start", "--foreground"])
    return cmd


def spawn_background_daemon(*, verbose: bool = False) -> subprocess.Popen[bytes]:
    """Start the daemon in a detached process; returns immediately."""
    popen_kwargs: dict[str, object] = {
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = _DETACHED_FLAGS
    else:
        popen_kwargs["start_new_session"] = True
    return subprocess.Popen(_daemon_command(verbose=verbose), **popen_kwargs)  # type: ignore[arg-type]


async def _ping_daemon() -> bool:
    try:
        client = IpcClient()
        await client.ping()
    except IpcConnectionError:
        return False
    else:
        return True


def wait_for_daemon_ready(*, timeout: float = 15.0, poll_interval: float = 0.2) -> int:
    """Block until the daemon responds to IPC ping or raise TimeoutError."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if is_daemon_running():
            if asyncio.run(_ping_daemon()):
                info = IpcClient().info
                return info.pid
        time.sleep(poll_interval)
    msg = "Timed out waiting for sybl daemon to start"
    raise TimeoutError(msg)
