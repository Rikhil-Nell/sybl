"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolate_sybl_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Redirect sybl config/state away from the real user profile."""
    config_dir = tmp_path / "config"
    state_dir = tmp_path / "state"
    config_dir.mkdir()
    state_dir.mkdir()
    monkeypatch.setenv("SYBL_CONFIG_DIR", str(config_dir))
    monkeypatch.setenv("SYBL_STATE_DIR", str(state_dir))


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


@pytest.fixture
def tmp_log_path(tmp_path: Path) -> Path:
    return tmp_path / "sybl.log"
