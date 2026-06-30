"""Dotted-path read/write helpers for SyblConfig."""

from __future__ import annotations

import json
from typing import Any

from sybl.config.manager import ConfigError
from sybl.config.models import SyblConfig


def parse_config_value(raw: str) -> Any:
    """Parse a CLI string into a TOML-compatible Python value."""
    stripped = raw.strip()
    lower = stripped.lower()
    if lower in ("true", "false"):
        return lower == "true"
    if (stripped.startswith('"') and stripped.endswith('"')) or (
        stripped.startswith("'") and stripped.endswith("'")
    ):
        return stripped[1:-1]
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        pass
    try:
        if "." in stripped:
            return float(stripped)
        return int(stripped)
    except ValueError:
        return stripped


def get_dotted(config: SyblConfig, path: str) -> Any:
    parts = [part.strip() for part in path.split(".") if part.strip()]
    if not parts:
        raise ConfigError("Config path must not be empty")

    current: Any = config.model_dump(mode="python")
    for part in parts:
        if not isinstance(current, dict) or part not in current:
            raise ConfigError(f"Unknown config path: {path!r}")
        current = current[part]
    return current


def set_dotted(config: SyblConfig, path: str, raw_value: str) -> SyblConfig:
    parts = [part.strip() for part in path.split(".") if part.strip()]
    if not parts:
        raise ConfigError("Config path must not be empty")

    value = parse_config_value(raw_value)
    data = config.model_dump(mode="python")
    target: dict[str, Any] = data
    for part in parts[:-1]:
        nested = target.get(part)
        if not isinstance(nested, dict):
            raise ConfigError(f"Unknown config path: {path!r}")
        target = nested
    leaf = parts[-1]
    if leaf not in target:
        raise ConfigError(f"Unknown config path: {path!r}")
    target[leaf] = value
    try:
        return SyblConfig.model_validate(data)
    except Exception as exc:
        raise ConfigError(f"Invalid value for {path!r}: {exc}") from exc


def dotted_to_patch(path: str, value: Any) -> dict[str, Any]:
    parts = [part.strip() for part in path.split(".") if part.strip()]
    if not parts:
        raise ConfigError("Config path must not be empty")

    patch: dict[str, Any] = {}
    cursor = patch
    for part in parts[:-1]:
        cursor[part] = {}
        cursor = cursor[part]
    cursor[parts[-1]] = value
    return patch
