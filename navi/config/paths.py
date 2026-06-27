"""Configuration path helpers."""

from pathlib import Path

from platformdirs import user_config_dir, user_state_dir

APP_NAME = "navi"
CONFIG_FILENAME = "config.toml"
LOG_FILENAME = "navi.log"


def config_dir() -> Path:
    path = Path(user_config_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / CONFIG_FILENAME


def state_dir() -> Path:
    path = Path(user_state_dir(APP_NAME))
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_path() -> Path:
    return state_dir() / LOG_FILENAME
