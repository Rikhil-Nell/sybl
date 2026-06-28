"""Tests for daemon single-instance lock."""

from __future__ import annotations

import os

import pytest

from navi.ipc.protocol import DaemonInfo
from navi.ipc.single_instance import DaemonAlreadyRunningError, DaemonLock


def test_acquire_and_release(tmp_path) -> None:
    lock = DaemonLock(path=tmp_path / "daemon.lock", info_path=tmp_path / "daemon.json")
    lock.acquire()
    assert lock.path.exists()
    lock.release()
    assert not lock.path.exists()
    assert not lock.info_path.exists()


def test_acquire_rejects_live_pid(tmp_path, monkeypatch) -> None:
    lock = DaemonLock(path=tmp_path / "daemon.lock", info_path=tmp_path / "daemon.json")
    lock.write_info(
        DaemonInfo(
            pid=os.getpid(),
            host="127.0.0.1",
            command_port=12345,
            event_port=12346,
            token="secret",
        )
    )
    with pytest.raises(DaemonAlreadyRunningError):
        lock.acquire()
