"""Tests for indicator sound cues."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
import soundfile as sf

from sybl.config.models import IndicatorConfig
from sybl.config.sounds import resolve_sound_path
from sybl.indicator.sound import (
    IndicatorSoundCue,
    _load_wav,
    _synthesize_chime,
    create_sound_cue,
)


def test_sound_disabled_is_noop() -> None:
    cue = IndicatorSoundCue(IndicatorConfig(sound_enabled=False))
    with patch("sybl.indicator.sound.sd.play") as play:
        cue.play_start()
        cue.play_stop()
    play.assert_not_called()


def test_sound_enabled_plays_chime() -> None:
    cue = IndicatorSoundCue(IndicatorConfig(sound_enabled=True, sound_volume=0.5))
    with (
        patch("sybl.indicator.sound.sd.play") as play,
        patch("sybl.indicator.sound.sd.stop"),
    ):
        cue.play_start()
        cue.play_stop()
    assert play.call_count == 2
    wave = play.call_args_list[0].args[0]
    assert isinstance(wave, np.ndarray)
    assert float(np.max(np.abs(wave))) <= 0.5


def test_synthesize_chime_is_normalized() -> None:
    wave = _synthesize_chime(((440.0, 0.05), (880.0, 0.05)))
    assert wave.dtype == np.float32
    assert float(np.max(np.abs(wave))) == 1.0


def test_load_wav_trims_to_max_seconds(tmp_path: Path) -> None:
    sample_rate = 44_100
    duration = 1.0
    t = np.linspace(0.0, duration, int(sample_rate * duration), endpoint=False)
    wave = (0.5 * np.sin(2.0 * np.pi * 440.0 * t)).astype(np.float32)
    path = tmp_path / "long.wav"
    sf.write(path, wave, sample_rate)

    loaded, rate = _load_wav(path, max_seconds=0.25)
    assert rate == 44_100
    assert len(loaded) == int(sample_rate * 0.25)


def test_custom_wav_used_when_present(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    path = sounds / "start.wav"
    sf.write(path, np.array([0.5, -0.5], dtype=np.float32), 44_100)
    monkeypatch.setattr("sybl.config.sounds.sounds_dir", lambda: sounds)

    cue = IndicatorSoundCue(IndicatorConfig(sound_enabled=True))
    assert cue._start_wave.shape[0] == 2


def test_resolve_sound_path_prefers_sounds_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    custom = sounds / "ping.wav"
    custom.write_bytes(b"")
    monkeypatch.setattr("sybl.config.sounds.sounds_dir", lambda: sounds)

    assert resolve_sound_path("ping.wav", default_name="start.wav") == custom


def test_create_sound_cue_factory() -> None:
    cue = create_sound_cue(IndicatorConfig())
    assert isinstance(cue, IndicatorSoundCue)
