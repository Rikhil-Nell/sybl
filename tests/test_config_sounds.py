"""Tests for config sound cue helpers."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from sybl.config.manager import ConfigManager
from sybl.config.sounds import (
    SoundCueError,
    clear_sound_cue,
    import_sound_cue,
    list_sound_files,
    resolve_sound_path,
)


def test_init_creates_sounds_layout(tmp_config_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("SYBL_CONFIG_DIR", str(tmp_config_path.parent))
    manager = ConfigManager(tmp_config_path)
    manager.init()
    sounds = tmp_config_path.parent / "sounds"
    assert sounds.is_dir()
    assert (sounds / "README.txt").is_file()


def test_import_and_list_sound_cue(tmp_path: Path, monkeypatch) -> None:
    config_home = tmp_path / "cfg"
    config_home.mkdir()
    monkeypatch.setenv("SYBL_CONFIG_DIR", str(config_home))
    source = tmp_path / "custom.wav"
    sf.write(source, np.array([0.25, -0.25], dtype=np.float32), 44_100)

    filename = import_sound_cue(source, "start")
    assert filename == "start.wav"
    assert list_sound_files() == ["start.wav"]
    assert resolve_sound_path("start.wav", default_name="start.wav") is not None

    clear_sound_cue("start")
    assert list_sound_files() == []


def test_import_rejects_non_wav(tmp_path: Path, monkeypatch) -> None:
    config_home = tmp_path / "cfg"
    config_home.mkdir()
    monkeypatch.setenv("SYBL_CONFIG_DIR", str(config_home))
    bad = tmp_path / "note.txt"
    bad.write_text("nope", encoding="utf-8")
    with pytest.raises(SoundCueError, match="\\.wav"):
        import_sound_cue(bad, "stop")
