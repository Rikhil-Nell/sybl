"""Single-instance lock for the sybl daemon."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from sybl.config.paths import state_dir
from sybl.ipc.process import is_pid_alive as check_pid_alive
from sybl.ipc.protocol import DaemonInfo


class DaemonAlreadyRunningError(Exception):
    """Raised when another daemon instance holds the lock."""


@dataclass(frozen=True)
class DaemonLock:
    path: Path
    info_path: Path

    @classmethod
    def default(cls) -> DaemonLock:
        base = state_dir()
        return cls(path=base / "daemon.lock", info_path=base / "daemon.json")

    def read_info(self) -> DaemonInfo | None:
        if not self.info_path.exists():
            return None
        try:
            data = json.loads(self.info_path.read_text(encoding="utf-8"))
            return DaemonInfo.model_validate(data)
        except (OSError, json.JSONDecodeError, ValueError):
            return None

    def write_info(self, info: DaemonInfo) -> None:
        self.info_path.parent.mkdir(parents=True, exist_ok=True)
        self.info_path.write_text(
            info.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def clear_info(self) -> None:
        if self.info_path.exists():
            self.info_path.unlink()

    def is_pid_alive(self, pid: int) -> bool:
        return check_pid_alive(pid)

    def acquire(self) -> None:
        existing = self.read_info()
        if existing is not None and check_pid_alive(existing.pid):
            raise DaemonAlreadyRunningError(
                f"Daemon already running (pid={existing.pid}). "
                "Use `sybl status` or `sybl stop`."
            )
        self.release()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(str(os.getpid()), encoding="utf-8")

    def release(self) -> None:
        if self.path.exists():
            self.path.unlink()
        self.clear_info()
