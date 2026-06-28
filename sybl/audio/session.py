"""Audio capture session — callback thread to asyncio queue."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Self

import numpy as np
import sounddevice as sd

from sybl.audio.devices import get_device_name, resolve_device
from sybl.audio.errors import SessionError, StreamError
from sybl.audio.metering import (
    SILENCE_DBFS,
    apply_meter_ballistics,
    compute_rms,
    display_level_from_dbfs,
    level_from_display,
    pcm_peak_dbfs,
)
from sybl.audio.resample import resample_pcm
from sybl.audio.types import (
    TARGET_SAMPLE_RATE,
    AudioChunk,
    CaptureStats,
)
from sybl.config.models import AudioConfig

logger = logging.getLogger("sybl.audio.session")

_SENTINEL = object()


class AudioCaptureSession:
    """Capture microphone audio as 16 kHz mono int16 PCM."""

    def __init__(self, config: AudioConfig) -> None:
        self._config = config
        self._device_index = resolve_device(config.device)
        self._device_name = get_device_name(self._device_index)
        self._loop: asyncio.AbstractEventLoop | None = None
        self._raw_queue: asyncio.Queue[bytes | object] | None = None
        self._chunk_queue: asyncio.Queue[AudioChunk | object] | None = None
        self._stream: sd.InputStream | None = None
        self._pump_task: asyncio.Task[None] | None = None
        self._native_rate = TARGET_SAMPLE_RATE
        self._needs_resample = False
        self._recording = False
        self._current_rms = 0.0
        self._current_level = 0.0
        self._peak_rms = 0.0
        self._peak_dbfs = SILENCE_DBFS
        self._chunk_count = 0
        self._bytes_captured = 0
        self._start_time = 0.0
        self._buffer: list[bytes] = []
        self._status_warning = False
        self._stream_error: Exception | None = None

    @property
    def current_rms(self) -> float:
        return self._current_rms

    @property
    def current_level(self) -> float:
        """Smoothed 0–1 level for UI meters (dBFS-scaled peak with ballistics)."""
        return self._current_level

    @property
    def current_dbfs(self) -> float:
        return level_from_display(self._current_level)

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def device_name(self) -> str:
        return self._device_name

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._recording:
            await self.cancel()

    async def start(self) -> None:
        if self._recording:
            raise SessionError("Session is already recording")

        self._loop = asyncio.get_running_loop()
        self._raw_queue = asyncio.Queue()
        self._chunk_queue = asyncio.Queue()
        self._buffer = []
        self._chunk_count = 0
        self._bytes_captured = 0
        self._peak_rms = 0.0
        self._current_rms = 0.0
        self._current_level = 0.0
        self._peak_dbfs = SILENCE_DBFS
        self._status_warning = False
        self._stream_error = None
        self._start_time = time.monotonic()

        device_info = sd.query_devices(self._device_index)
        native_rate = int(device_info["default_samplerate"])
        rates_to_try = (
            [native_rate, TARGET_SAMPLE_RATE]
            if native_rate != TARGET_SAMPLE_RATE
            else [TARGET_SAMPLE_RATE]
        )

        last_error: sd.PortAudioError | None = None
        for rate in rates_to_try:
            blocksize = max(
                1,
                int(rate * self._config.block_duration_ms / 1000),
            )
            try:
                self._stream = self._open_stream(rate, blocksize)
                self._native_rate = rate
                self._needs_resample = rate != TARGET_SAMPLE_RATE
                break
            except sd.PortAudioError as exc:
                last_error = exc
        else:
            raise StreamError(
                f"Could not open input device {self._device_name!r}: {last_error}"
            ) from last_error

        if self._needs_resample:
            logger.info(
                "Opened device at native rate %d Hz (resample to %d Hz)",
                self._native_rate,
                TARGET_SAMPLE_RATE,
            )

        self._stream.start()
        self._recording = True
        self._pump_task = asyncio.create_task(self._pump())
        logger.info(
            "Recording started (device=%s, rate=%d)",
            self._device_name,
            self._native_rate,
        )

    def _open_stream(self, samplerate: int, blocksize: int) -> sd.InputStream:
        return sd.InputStream(
            device=self._device_index,
            channels=self._config.channels,
            samplerate=samplerate,
            dtype="int16",
            blocksize=blocksize,
            callback=self._callback,
        )

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        if status:
            self._status_warning = True
        if self._loop is None or self._raw_queue is None:
            return
        raw_bytes = indata.tobytes()
        self._loop.call_soon_threadsafe(self._raw_queue.put_nowait, raw_bytes)

    async def _pump(self) -> None:
        assert self._raw_queue is not None
        assert self._chunk_queue is not None

        if self._status_warning:
            logger.warning("Audio stream reported overflow/underflow")
            self._status_warning = False

        try:
            while True:
                raw = await self._raw_queue.get()
                if raw is _SENTINEL:
                    break

                assert isinstance(raw, bytes)
                pcm = (
                    resample_pcm(raw, self._native_rate, TARGET_SAMPLE_RATE)
                    if self._needs_resample
                    else raw
                )
                rms = compute_rms(pcm)
                peak_dbfs = pcm_peak_dbfs(pcm)
                peak_level = display_level_from_dbfs(peak_dbfs)
                self._current_rms = rms
                self._current_level = apply_meter_ballistics(
                    self._current_level,
                    peak_level,
                )
                self._peak_rms = max(self._peak_rms, rms)
                self._peak_dbfs = max(self._peak_dbfs, peak_dbfs)
                self._chunk_count += 1
                self._bytes_captured += len(pcm)
                self._buffer.append(pcm)

                chunk = AudioChunk(
                    pcm=pcm,
                    sample_rate=TARGET_SAMPLE_RATE,
                    timestamp=time.monotonic(),
                    rms=rms,
                )
                await self._chunk_queue.put(chunk)
        except Exception as exc:
            self._stream_error = exc
            logger.exception("Audio pump failed")
        finally:
            await self._chunk_queue.put(_SENTINEL)

    async def stop(self) -> bytes:
        if not self._recording:
            raise SessionError("Session is not recording")

        self._recording = False
        await self._teardown()

        if self._stream_error is not None:
            raise StreamError(f"Audio stream failed: {self._stream_error}") from (
                self._stream_error
            )

        return b"".join(self._buffer)

    async def cancel(self) -> None:
        if not self._recording:
            return
        self._recording = False
        self._buffer = []
        await self._teardown()

    async def _teardown(self) -> None:
        if self._stream is not None:
            try:
                if self._stream.active:
                    self._stream.stop()
            except sd.PortAudioError as exc:
                logger.warning("Error stopping stream: %s", exc)
            finally:
                self._stream.close()
                self._stream = None

        if self._raw_queue is not None:
            await self._raw_queue.put(_SENTINEL)

        if self._pump_task is not None:
            try:
                await self._pump_task
            except asyncio.CancelledError:
                pass
            self._pump_task = None

    async def chunks(self) -> AsyncIterator[AudioChunk]:
        if self._chunk_queue is None:
            raise SessionError("Session has not been started")
        while True:
            item = await self._chunk_queue.get()
            if item is _SENTINEL:
                break
            assert isinstance(item, AudioChunk)
            yield item

    def stats(self) -> CaptureStats:
        duration = time.monotonic() - self._start_time if self._start_time else 0.0
        return CaptureStats(
            duration_seconds=duration,
            chunk_count=self._chunk_count,
            peak_rms=self._peak_rms,
            peak_dbfs=self._peak_dbfs,
            device_name=self._device_name,
            bytes_captured=self._bytes_captured,
        )
