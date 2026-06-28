"""Tests for audio capture pipeline."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import soundfile as sf
from typer.testing import CliRunner

from sybl.audio.debug import debug_recording_dir, default_recording_path, save_wav
from sybl.audio.devices import _dedupe_devices, resolve_device
from sybl.audio.errors import DeviceNotFoundError, SessionError
from sybl.audio.metering import (
    apply_meter_ballistics,
    compute_rms,
    display_level_from_dbfs,
    pcm_peak_dbfs,
)
from sybl.audio.resample import resample_pcm
from sybl.audio.session import AudioCaptureSession
from sybl.audio.types import TARGET_SAMPLE_RATE, DeviceInfo
from sybl.cli import app
from sybl.config.models import AudioConfig

runner = CliRunner()

FAKE_DEVICES = [
    DeviceInfo(
        index=0,
        name="Built-in Microphone",
        default_samplerate=48000.0,
        max_input_channels=2,
        is_default=True,
    ),
    DeviceInfo(
        index=3,
        name="USB Headset Mic",
        default_samplerate=44100.0,
        max_input_channels=1,
        is_default=False,
    ),
]


def _sine_pcm(
    frequency: float,
    sample_rate: int,
    duration_seconds: float,
    amplitude: float = 0.5,
) -> bytes:
    t = np.linspace(
        0,
        duration_seconds,
        int(sample_rate * duration_seconds),
        endpoint=False,
    )
    samples = (amplitude * 32767 * np.sin(2 * np.pi * frequency * t)).astype(np.int16)
    return samples.tobytes()


@patch("sybl.audio.devices.list_input_devices", return_value=FAKE_DEVICES)
@patch("sybl.audio.devices.sd.default.device", (0, 1))
def test_resolve_device_default(_mock_list: MagicMock) -> None:
    assert resolve_device(None) == 0


@patch("sybl.audio.devices.list_input_devices", return_value=FAKE_DEVICES)
def test_resolve_device_by_index(_mock_list: MagicMock) -> None:
    assert resolve_device("3") == 3


@patch("sybl.audio.devices.list_input_devices", return_value=FAKE_DEVICES)
def test_resolve_device_by_name_substring(_mock_list: MagicMock) -> None:
    assert resolve_device("usb") == 3


@patch("sybl.audio.devices.list_input_devices", return_value=FAKE_DEVICES)
def test_resolve_device_by_exact_name(_mock_list: MagicMock) -> None:
    assert resolve_device("Built-in Microphone") == 0


@patch("sybl.audio.devices.list_input_devices", return_value=FAKE_DEVICES)
def test_resolve_device_not_found(_mock_list: MagicMock) -> None:
    with pytest.raises(DeviceNotFoundError, match="No input device"):
        resolve_device("nonexistent")


@patch("sybl.audio.devices.list_input_devices", return_value=FAKE_DEVICES)
def test_resolve_device_invalid_index(_mock_list: MagicMock) -> None:
    with pytest.raises(DeviceNotFoundError, match="Device index 99"):
        resolve_device("99")


def test_resample_48k_to_16k() -> None:
    pcm = _sine_pcm(440.0, 48000, 0.1)
    out = resample_pcm(pcm, 48000, TARGET_SAMPLE_RATE)
    expected_samples = int(0.1 * TARGET_SAMPLE_RATE)
    assert len(out) == expected_samples * 2


def test_resample_44k_to_16k() -> None:
    pcm = _sine_pcm(440.0, 44100, 0.1)
    out = resample_pcm(pcm, 44100, TARGET_SAMPLE_RATE)
    expected_samples = int(0.1 * TARGET_SAMPLE_RATE)
    assert abs(len(out) - expected_samples * 2) <= 4


def test_resample_same_rate_passthrough() -> None:
    pcm = _sine_pcm(440.0, TARGET_SAMPLE_RATE, 0.05)
    assert resample_pcm(pcm, TARGET_SAMPLE_RATE) == pcm


def test_compute_rms_silent() -> None:
    pcm = np.zeros(1000, dtype=np.int16).tobytes()
    assert compute_rms(pcm) == 0.0


def test_compute_rms_loud() -> None:
    pcm = np.full(1000, 16000, dtype=np.int16).tobytes()
    rms = compute_rms(pcm)
    assert 0.45 < rms < 0.55


def test_display_level_from_dbfs_quiet() -> None:
    assert display_level_from_dbfs(-60.0) == 0.0


def test_display_level_from_dbfs_loud() -> None:
    level = display_level_from_dbfs(-20.0)
    assert level > 0.5


def test_pcm_peak_dbfs_speech_like() -> None:
    pcm = np.full(320, 3000, dtype=np.int16).tobytes()
    dbfs = pcm_peak_dbfs(pcm)
    assert -30.0 < dbfs < -10.0


def test_meter_ballistics_attack_and_release() -> None:
    current = 0.0
    current = apply_meter_ballistics(current, 1.0)
    assert current > 0.5
    current = apply_meter_ballistics(current, 0.0)
    assert 0.0 < current < 0.5


@patch("sybl.audio.devices.sd.query_devices")
def test_dedupe_devices_prefers_default(mock_query_devices: MagicMock) -> None:
    mock_query_devices.side_effect = lambda index: {"hostapi": 0}
    devices = [
        DeviceInfo(0, "Mic", 48000.0, 2, is_default=False),
        DeviceInfo(5, "Mic", 48000.0, 2, is_default=True),
    ]
    deduped = _dedupe_devices(devices)
    assert len(deduped) == 1
    assert deduped[0].index == 5


def test_default_recording_path_uses_debug_folder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sybl.audio.debug as debug_module

    monkeypatch.setattr(debug_module, "state_dir", lambda: Path("/tmp/sybl-state"))
    path = default_recording_path()
    assert path.parent.name == "debug recording"
    assert path.name == "last_recording.wav"


def test_debug_recording_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    import sybl.audio.debug as debug_module

    monkeypatch.setattr(debug_module, "state_dir", lambda: tmp_path)
    folder = debug_recording_dir()
    assert folder == tmp_path / "debug recording"
    assert folder.is_dir()


def test_save_wav_round_trip(tmp_path: Path) -> None:
    pcm = _sine_pcm(440.0, TARGET_SAMPLE_RATE, 0.1)
    path = tmp_path / "test.wav"
    save_wav(path, pcm)

    data, rate = sf.read(path, dtype="int16")
    assert rate == TARGET_SAMPLE_RATE
    assert data.ndim == 1
    assert len(data) == len(pcm) // 2


class FakeInputStream:
    instances: list[FakeInputStream] = []

    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.active = False
        self.callback = kwargs.get("callback")
        FakeInputStream.instances.append(self)

    def start(self) -> None:
        self.active = True

    def stop(self) -> None:
        self.active = False

    def close(self) -> None:
        self.active = False


@pytest.mark.asyncio
async def test_session_start_stop() -> None:
    FakeInputStream.instances.clear()
    config = AudioConfig(block_duration_ms=20)

    with (
        patch("sybl.audio.session.resolve_device", return_value=0),
        patch("sybl.audio.session.get_device_name", return_value="Test Mic"),
        patch(
            "sybl.audio.session.sd.query_devices",
            return_value={"default_samplerate": 16000, "name": "Test Mic"},
        ),
        patch("sybl.audio.session.sd.InputStream", FakeInputStream),
    ):
        session = AudioCaptureSession(config)
        await session.start()
        assert session.is_recording
        assert FakeInputStream.instances

        pcm = await session.stop()
        assert isinstance(pcm, bytes)
        assert not session.is_recording


@pytest.mark.asyncio
async def test_session_cancel_discards() -> None:
    config = AudioConfig()
    with (
        patch("sybl.audio.session.resolve_device", return_value=0),
        patch("sybl.audio.session.get_device_name", return_value="Test Mic"),
        patch(
            "sybl.audio.session.sd.query_devices",
            return_value={"default_samplerate": 16000, "name": "Test Mic"},
        ),
        patch("sybl.audio.session.sd.InputStream", FakeInputStream),
    ):
        session = AudioCaptureSession(config)
        await session.start()
        await session.cancel()
        assert not session.is_recording


@pytest.mark.asyncio
async def test_session_double_start_raises() -> None:
    config = AudioConfig()
    with (
        patch("sybl.audio.session.resolve_device", return_value=0),
        patch("sybl.audio.session.get_device_name", return_value="Test Mic"),
        patch(
            "sybl.audio.session.sd.query_devices",
            return_value={"default_samplerate": 16000, "name": "Test Mic"},
        ),
        patch("sybl.audio.session.sd.InputStream", FakeInputStream),
    ):
        session = AudioCaptureSession(config)
        await session.start()
        with pytest.raises(SessionError, match="already recording"):
            await session.start()
        await session.cancel()


@pytest.mark.asyncio
async def test_session_pump_processes_callback_data() -> None:
    FakeInputStream.instances.clear()
    config = AudioConfig(block_duration_ms=20)
    with (
        patch("sybl.audio.session.resolve_device", return_value=0),
        patch("sybl.audio.session.get_device_name", return_value="Test Mic"),
        patch(
            "sybl.audio.session.sd.query_devices",
            return_value={"default_samplerate": 16000, "name": "Test Mic"},
        ),
        patch("sybl.audio.session.sd.InputStream", FakeInputStream),
    ):
        session = AudioCaptureSession(config)
        await session.start()

        stream = FakeInputStream.instances[-1]
        callback = stream.callback
        assert callback is not None

        frame_count = int(TARGET_SAMPLE_RATE * 0.02)
        indata = np.zeros((frame_count, 1), dtype=np.int16)
        indata[:, 0] = 8000
        callback(indata, frame_count, None, MagicMock())

        await asyncio.sleep(0.1)
        assert session.current_level > 0.0

        pcm = await session.stop()
        assert len(pcm) > 0


def test_audio_devices_help() -> None:
    result = runner.invoke(app, ["audio", "devices", "--help"])
    assert result.exit_code == 0


def test_audio_record_help() -> None:
    result = runner.invoke(
        app,
        ["audio", "record", "--help"],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )
    assert result.exit_code == 0
    assert "--seconds" in result.stdout


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_from_real_mic() -> None:
    config = AudioConfig()
    async with AudioCaptureSession(config) as session:
        await session.start()
        await asyncio.sleep(0.5)
        pcm = await session.stop()
    assert len(pcm) > 0
