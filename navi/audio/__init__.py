"""Audio capture pipeline (Phase 1)."""

from navi.audio.debug import (
    debug_recording_dir,
    default_recording_path,
    save_wav,
)
from navi.audio.devices import list_input_devices, resolve_device
from navi.audio.errors import (
    AudioError,
    DeviceNotFoundError,
    SessionError,
    StreamError,
)
from navi.audio.session import AudioCaptureSession
from navi.audio.types import (
    TARGET_SAMPLE_RATE,
    AudioChunk,
    CaptureStats,
    DeviceInfo,
)

__all__ = [
    "TARGET_SAMPLE_RATE",
    "AudioCaptureSession",
    "AudioChunk",
    "AudioError",
    "CaptureStats",
    "DeviceInfo",
    "DeviceNotFoundError",
    "SessionError",
    "StreamError",
    "default_recording_path",
    "debug_recording_dir",
    "list_input_devices",
    "resolve_device",
    "save_wav",
]
