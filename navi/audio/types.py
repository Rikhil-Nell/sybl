"""Audio capture data types."""

from __future__ import annotations

from dataclasses import dataclass

TARGET_SAMPLE_RATE = 16_000


@dataclass(frozen=True)
class DeviceInfo:
    index: int
    name: str
    default_samplerate: float
    max_input_channels: int
    is_default: bool = False


@dataclass(frozen=True)
class AudioChunk:
    pcm: bytes
    sample_rate: int
    timestamp: float
    rms: float


@dataclass(frozen=True)
class CaptureStats:
    duration_seconds: float
    chunk_count: int
    peak_rms: float
    peak_dbfs: float
    device_name: str
    bytes_captured: int
