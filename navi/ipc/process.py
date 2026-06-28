"""Process liveness checks (cross-platform)."""

from __future__ import annotations

import os
import sys


def is_pid_alive(pid: int) -> bool:
    """Return True if a process with ``pid`` appears to be running."""
    if pid <= 0:
        return False

    if sys.platform == "win32":
        import ctypes

        synchronize = 0x00100000
        handle = ctypes.windll.kernel32.OpenProcess(synchronize, False, pid)
        if not handle:
            return False
        ctypes.windll.kernel32.CloseHandle(handle)
        return True

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True
