"""Signal level metering."""

from __future__ import annotations

import math

import numpy as np

INT16_MAX = 32768.0
SILENCE_DBFS = -80.0
METER_FLOOR_DBFS = -55.0
METER_CEILING_DBFS = -10.0


def compute_rms(pcm: bytes) -> float:
    """Return normalized RMS level in 0.0–1.0 from int16 PCM bytes."""
    if not pcm:
        return 0.0
    samples = np.frombuffer(pcm, dtype=np.int16).astype(np.float64)
    if samples.size == 0:
        return 0.0
    rms = float(np.sqrt(np.mean(samples**2)))
    return min(rms / INT16_MAX, 1.0)


def compute_peak(pcm: bytes) -> float:
    """Return normalized peak level in 0.0–1.0 from int16 PCM bytes."""
    if not pcm:
        return 0.0
    samples = np.frombuffer(pcm, dtype=np.int16)
    if samples.size == 0:
        return 0.0
    peak = float(np.max(np.abs(samples.astype(np.int32))))
    return min(peak / INT16_MAX, 1.0)


def level_to_dbfs(normalized: float) -> float:
    """Convert a normalized 0–1 level to dBFS."""
    if normalized <= 0.0:
        return SILENCE_DBFS
    return max(SILENCE_DBFS, 20.0 * math.log10(normalized))


def pcm_peak_dbfs(pcm: bytes) -> float:
    return level_to_dbfs(compute_peak(pcm))


def display_level_from_dbfs(
    dbfs: float,
    *,
    floor_dbfs: float = METER_FLOOR_DBFS,
    ceiling_dbfs: float = METER_CEILING_DBFS,
) -> float:
    """Map dBFS into 0.0–1.0 for a responsive level meter."""
    if dbfs <= floor_dbfs:
        return 0.0
    if dbfs >= ceiling_dbfs:
        return 1.0
    return (dbfs - floor_dbfs) / (ceiling_dbfs - floor_dbfs)


def level_from_display(display: float) -> float:
    """Convert smoothed 0–1 meter level back to dBFS for display."""
    return METER_FLOOR_DBFS + display * (METER_CEILING_DBFS - METER_FLOOR_DBFS)


def apply_meter_ballistics(
    current: float,
    new_peak: float,
    *,
    attack: float = 0.55,
    release: float = 0.12,
) -> float:
    """Fast attack, slower release — snappy but readable meter."""
    if new_peak >= current:
        return current + (new_peak - current) * attack
    return current + (new_peak - current) * release
