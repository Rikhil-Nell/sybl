"""Optional audio cues when dictation starts or stops."""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
import soxr

from sybl.config.models import IndicatorConfig
from sybl.config.sounds import DEFAULT_CUE_NAMES, resolve_sound_path

logger = logging.getLogger("sybl.indicator.sound")

_SAMPLE_RATE = 44_100

_START_NOTES: tuple[tuple[float, float], ...] = ((523.25, 0.07), (659.25, 0.11))
_STOP_NOTES: tuple[tuple[float, float], ...] = ((659.25, 0.07), (523.25, 0.09))


class IndicatorSoundCue:
    """Play custom WAV cues or built-in chimes on listen start/stop."""

    def __init__(self, config: IndicatorConfig) -> None:
        self._config = config
        self._lock = threading.Lock()
        self._start_wave, self._start_rate = self._load_cue(
            config.sound_start_file,
            default_name=DEFAULT_CUE_NAMES["start"],
            fallback=_synthesize_chime(_START_NOTES),
        )
        self._stop_wave, self._stop_rate = self._load_cue(
            config.sound_stop_file,
            default_name=DEFAULT_CUE_NAMES["stop"],
            fallback=_synthesize_chime(_STOP_NOTES),
        )

    def play_start(self) -> None:
        if not self._config.sound_enabled or not self._config.sound_on_start:
            return
        self._play(self._start_wave, self._start_rate)

    def play_stop(self) -> None:
        if not self._config.sound_enabled or not self._config.sound_on_stop:
            return
        self._play(self._stop_wave, self._stop_rate)

    def shutdown(self) -> None:
        return

    def _load_cue(
        self,
        configured: str | None,
        *,
        default_name: str,
        fallback: np.ndarray,
    ) -> tuple[np.ndarray, int]:
        path = resolve_sound_path(configured, default_name=default_name)
        if path is None:
            return fallback, _SAMPLE_RATE
        try:
            return _load_wav(path, self._config.sound_max_seconds)
        except Exception:
            logger.warning(
                "Failed to load cue %s; using built-in chime",
                path,
                exc_info=True,
            )
            return fallback, _SAMPLE_RATE

    def _play(self, wave: np.ndarray, sample_rate: int) -> None:
        volume = self._config.sound_volume
        if volume <= 0:
            return
        scaled = np.clip(wave * volume, -1.0, 1.0).astype(np.float32)
        try:
            with self._lock:
                sd.stop()
                sd.play(scaled, sample_rate, blocking=False)
        except Exception:
            logger.debug("Indicator sound playback failed", exc_info=True)


def _load_wav(path: Path, max_seconds: float) -> tuple[np.ndarray, int]:
    data, sample_rate = sf.read(path, dtype="float32", always_2d=False)
    if data.ndim > 1:
        data = data.mean(axis=1)
    max_samples = int(sample_rate * max_seconds)
    if len(data) > max_samples:
        logger.info(
            "Trimmed sound cue %s to %.2fs (limit %.2fs)",
            path.name,
            max_seconds,
            max_seconds,
        )
        data = data[:max_samples]
    peak = float(np.max(np.abs(data))) or 1.0
    data = (data / peak).astype(np.float32)
    if sample_rate != _SAMPLE_RATE:
        data = soxr.resample(data, sample_rate, _SAMPLE_RATE).astype(np.float32)
        sample_rate = _SAMPLE_RATE
    return data, sample_rate


def _synthesize_chime(notes: tuple[tuple[float, float], ...]) -> np.ndarray:
    parts: list[np.ndarray] = []
    for frequency, duration in notes:
        sample_count = max(int(_SAMPLE_RATE * duration), 1)
        time_axis = np.linspace(0.0, duration, sample_count, endpoint=False)
        tone = np.sin(2.0 * np.pi * frequency * time_axis)
        envelope = np.linspace(1.0, 0.15, sample_count) ** 0.6
        parts.append(tone * envelope)
    wave = np.concatenate(parts)
    peak = float(np.max(np.abs(wave))) or 1.0
    return (wave / peak).astype(np.float32)


def create_sound_cue(config: IndicatorConfig) -> IndicatorSoundCue:
    return IndicatorSoundCue(config)
