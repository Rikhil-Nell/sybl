"""PCM to WAV conversion for provider uploads."""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf

from navi.audio.types import TARGET_SAMPLE_RATE


def pcm_to_wav_bytes(
    pcm: bytes,
    sample_rate: int = TARGET_SAMPLE_RATE,
) -> bytes:
    """Encode mono int16 PCM bytes as an in-memory WAV file."""
    buffer = io.BytesIO()
    samples = np.frombuffer(pcm, dtype=np.int16)
    sf.write(buffer, samples, sample_rate, subtype="PCM_16", format="WAV")
    return buffer.getvalue()
