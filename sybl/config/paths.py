"""Configuration path helpers."""

from __future__ import annotations

import os
from pathlib import Path

from platformdirs import user_config_dir, user_state_dir

APP_NAME = "sybl"
CONFIG_FILENAME = "config.toml"
VOCABULARY_FILENAME = "vocabulary.toml"
LOG_FILENAME = "sybl.log"


def _env_path(name: str) -> Path | None:
    raw = os.environ.get(name)
    if not raw:
        return None
    return Path(raw)


def config_dir() -> Path:
    override = _env_path("SYBL_CONFIG_DIR")
    path = override if override is not None else Path(user_config_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def state_dir() -> Path:
    override = _env_path("SYBL_STATE_DIR")
    path = override if override is not None else Path(user_state_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return state_dir() / LOG_FILENAME


def sounds_dir() -> Path:
    path = config_dir() / "sounds"
    path.mkdir(parents=True, exist_ok=True)
    return path


def vocabulary_path() -> Path:
    return state_dir() / VOCABULARY_FILENAME
