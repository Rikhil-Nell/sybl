"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_config_path(tmp_path: Path) -> Path:
    return tmp_path / "config.toml"


@pytest.fixture
def tmp_log_path(tmp_path: Path) -> Path:
    return tmp_path / "sybl.log"
