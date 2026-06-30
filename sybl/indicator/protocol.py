"""NDJSON command protocol for the pill overlay subprocess."""

from __future__ import annotations

import json
from typing import Any


def config_payload(
    *,
    size_px: int,
    anchor: str,
    margin_px: int,
    offset_x: int,
    offset_y: int,
    accent: str,
    accent_secondary: str,
    idle_opacity: float,
    fps: int,
) -> dict[str, Any]:
    return {
        "size_px": size_px,
        "anchor": anchor,
        "margin_px": margin_px,
        "offset_x": offset_x,
        "offset_y": offset_y,
        "accent": accent,
        "accent_secondary": accent_secondary,
        "idle_opacity": idle_opacity,
        "fps": fps,
    }


def serialize_command(command: dict[str, Any]) -> str:
    """Serialize one NDJSON command line (no trailing newline)."""
    return json.dumps(command, separators=(",", ":"), ensure_ascii=True)


def parse_command(line: str) -> dict[str, Any]:
    return json.loads(line)
