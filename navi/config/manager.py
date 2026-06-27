"""Load, save, and initialize Navi configuration."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from navi.config.models import NaviConfig
from navi.config.paths import config_path


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or validated."""


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or config_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> NaviConfig:
        if not self._path.exists():
            return NaviConfig()

        try:
            with self._path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Invalid TOML in {self._path}: {exc}") from exc

        try:
            return NaviConfig.model_validate(data)
        except Exception as exc:
            raise ConfigError(f"Invalid configuration in {self._path}: {exc}") from exc

    def save(self, config: NaviConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="python")
        with self._path.open("wb") as handle:
            tomli_w.dump(_prepare_for_toml(payload), handle)

    def init(self) -> NaviConfig:
        config = NaviConfig()
        self.save(config)
        return config


def _prepare_for_toml(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _prepare_for_toml(item)
            for key, item in value.items()
            if item is not None
        }
    if isinstance(value, list):
        return [_prepare_for_toml(item) for item in value]
    return value
