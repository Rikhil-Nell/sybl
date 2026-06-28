"""Debug utilities for audio capture."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf

from sybl.audio.types import TARGET_SAMPLE_RATE
from sybl.config.paths import state_dir

DEBUG_RECORDING_DIRNAME = "debug recording"
LAST_RECORDING_FILENAME = "last_recording.wav"


def debug_recording_dir() -> Path:
    path = state_dir() / DEBUG_RECORDING_DIRNAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def default_recording_path() -> Path:
    return debug_recording_dir() / LAST_RECORDING_FILENAME


def timestamped_recording_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return debug_recording_dir() / f"recording_{stamp}.wav"


def save_wav(
    path: Path,
    pcm: bytes,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> None:
    """Write mono int16 PCM bytes to a WAV file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    samples = np.frombuffer(pcm, dtype=np.int16)
    sf.write(path, samples, sample_rate, subtype="PCM_16")
