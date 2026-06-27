"""PCM resampling to the STT target format."""

from __future__ import annotations

import numpy as np
import soxr

from navi.audio.types import TARGET_SAMPLE_RATE


def resample_pcm(
    pcm: bytes,
    source_rate: int,
    target_rate: int = TARGET_SAMPLE_RATE,
) -> bytes:
    """Resample mono int16 PCM from source_rate to target_rate."""
    if source_rate == target_rate:
        return pcm
    if not pcm:
        return b""

    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float32)
    resampled = soxr.resample(samples, source_rate, target_rate, quality="HQ")
    clipped = np.clip(resampled, -32768, 32767).astype(np.int16)
    return clipped.tobytes()
