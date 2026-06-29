"""Sound cue files under the sybl config directory."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Literal

import soundfile as sf

from sybl.config.paths import config_dir, sounds_dir

logger = logging.getLogger("sybl.config.sounds")

SoundRole = Literal["start", "stop"]
DEFAULT_CUE_NAMES: dict[SoundRole, str] = {"start": "start.wav", "stop": "stop.wav"}
SOUNDS_README = """sybl sound cues
================

Drop WAV files here for listen start/stop sounds.

  start.wav  — plays when dictation begins
  stop.wav   — plays when dictation ends

Enable in config.toml ([indicator] sound_enabled = true) or TUI Settings.
Files longer than sound_max_seconds (default 0.5s) are trimmed automatically.
If a file is missing, sybl uses the built-in chime.
"""


class SoundCueError(Exception):
    """Raised when a sound cue file cannot be imported."""


def ensure_sounds_layout() -> Path:
    """Create the sounds folder and helper README if missing."""
    path = sounds_dir()
    readme = path / "README.txt"
    if not readme.exists():
        readme.write_text(SOUNDS_README, encoding="utf-8")
    return path


def list_sound_files() -> list[str]:
    ensure_sounds_layout()
    return sorted(
        file.name for file in sounds_dir().glob("*.wav") if file.is_file()
    )


def cue_path_for_role(role: SoundRole) -> Path:
    if role not in DEFAULT_CUE_NAMES:
        msg = f"Unknown sound role: {role!r}"
        raise SoundCueError(msg)
    return sounds_dir() / DEFAULT_CUE_NAMES[role]


def resolve_sound_path(configured: str | None, *, default_name: str) -> Path | None:
    if configured:
        candidate = Path(configured)
        if candidate.is_absolute():
            return candidate if candidate.is_file() else None
        for base in (sounds_dir(), config_dir()):
            path = base / configured
            if path.is_file():
                return path
        return None
    default = sounds_dir() / default_name
    return default if default.is_file() else None


def validate_wav_source(source: Path) -> None:
    if not source.is_file():
        msg = f"Sound file not found: {source}"
        raise SoundCueError(msg)
    if source.suffix.lower() != ".wav":
        msg = "Sound cues must be .wav files"
        raise SoundCueError(msg)
    try:
        sf.info(source)
    except Exception as exc:
        msg = f"Invalid WAV file: {source.name}"
        raise SoundCueError(msg) from exc


def import_sound_cue(source: Path, role: SoundRole) -> str:
    """Copy a WAV into the sounds folder for the given role."""
    ensure_sounds_layout()
    validate_wav_source(source)
    destination = cue_path_for_role(role)
    shutil.copy2(source, destination)
    logger.info("Imported %s sound cue from %s", role, source)
    return DEFAULT_CUE_NAMES[role]


def clear_sound_cue(role: SoundRole) -> None:
    """Remove the canonical cue file for a role, if present."""
    path = cue_path_for_role(role)
    if path.exists():
        path.unlink()
        logger.info("Removed %s sound cue", role)
