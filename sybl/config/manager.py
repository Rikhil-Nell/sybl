"""Load, save, and initialize sybl configuration."""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

import tomli_w

from sybl.config.models import SyblConfig
from sybl.config.paths import config_path
from sybl.hotkeys.bindings import BindingParseError, parse_binding

logger = logging.getLogger("sybl.config")

_LEGACY_HOTKEY_BINDING = "ctrl+shift+space"
_CURRENT_HOTKEY_BINDING = "ctrl+alt+space"


class ConfigError(Exception):
    """Raised when configuration cannot be loaded or validated."""


class ConfigManager:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or config_path()

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> SyblConfig:
        if not self._path.exists():
            return SyblConfig()

        try:
            with self._path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise ConfigError(f"Invalid TOML in {self._path}: {exc}") from exc

        try:
            config = SyblConfig.model_validate(data)
        except Exception as exc:
            raise ConfigError(f"Invalid configuration in {self._path}: {exc}") from exc

        migrated = _migrate_legacy_hotkey_binding(config)
        if migrated is not config:
            self.save(migrated)
            logger.info(
                "Updated hotkey binding from %s to %s (Windows Terminal conflict)",
                _LEGACY_HOTKEY_BINDING,
                _CURRENT_HOTKEY_BINDING,
            )
            return migrated

        return config

    def save(self, config: SyblConfig) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = config.model_dump(mode="python")
        with self._path.open("wb") as handle:
            tomli_w.dump(_prepare_for_toml(payload), handle)

    def init(self) -> SyblConfig:
        config = SyblConfig()
        self.save(config)
        return config


def _migrate_legacy_hotkey_binding(config: SyblConfig) -> SyblConfig:
    """Upgrade the old default binding that conflicts with Windows Terminal."""
    try:
        normalized = "+".join(parse_binding(config.hotkey.binding).tokens)
    except BindingParseError:
        return config

    if normalized != _LEGACY_HOTKEY_BINDING:
        return config

    return config.model_copy(
        update={
            "hotkey": config.hotkey.model_copy(
                update={"binding": _CURRENT_HOTKEY_BINDING}
            )
        }
    )


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
