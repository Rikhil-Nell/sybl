"""`navi audio` — device listing and capture testing."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

import typer

from navi.audio import (
    AudioCaptureSession,
    AudioError,
    default_recording_path,
    list_input_devices,
    save_wav,
)
from navi.config import AudioConfig, ConfigManager, log_path
from navi.logging import setup_logging

audio_app = typer.Typer(help="Audio capture commands (Phase 1).")


@audio_app.command("devices")
def audio_devices_command() -> None:
    """List microphone input devices that can be opened right now."""
    devices = list_input_devices()
    if not devices:
        typer.echo("No usable input devices found.")
        raise typer.Exit(code=1)

    typer.echo(f"{'IDX':>4}  {'DEFAULT':^7}  {'RATE':>8}  {'CH':>3}  NAME")
    typer.echo("-" * 60)
    for device in devices:
        default_marker = "*" if device.is_default else ""
        typer.echo(
            f"{device.index:4d}  {default_marker:^7}  "
            f"{device.default_samplerate:8.0f}  {device.max_input_channels:3d}  "
            f"{device.name}"
        )


@audio_app.command("record")
def audio_record_command(
    ctx: typer.Context,
    seconds: float | None = typer.Option(
        None,
        "--seconds",
        "-s",
        help="Record for this many seconds (default: press Enter to stop).",
    ),
    device: str | None = typer.Option(
        None,
        "--device",
        "-d",
        help="Override input device (index or name substring).",
    ),
    save_path: Path | None = typer.Option(
        None,
        "--save",
        "-o",
        help="Output WAV path.",
    ),
    no_save: bool = typer.Option(
        False,
        "--no-save",
        help="Do not write a WAV file.",
    ),
) -> None:
    """Record from the microphone and optionally save a debug WAV."""
    verbose = bool(ctx.obj and ctx.obj.get("verbose"))
    config_manager = ConfigManager()
    navi_config = config_manager.load()
    setup_logging(navi_config.logging, log_file=log_path(), verbose=verbose)

    audio_config = navi_config.audio.model_copy(
        update={"device": device if device is not None else navi_config.audio.device}
    )

    try:
        asyncio.run(
            _record(
                audio_config,
                seconds,
                save_path,
                no_save,
                navi_config.audio.save_last_recording,
            )
        )
    except AudioError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


async def _record(
    audio_config: AudioConfig,
    seconds: float | None,
    save_path: Path | None,
    no_save: bool,
    save_last_recording: bool,
) -> None:
    if seconds is not None:
        typer.echo(f"Recording for {seconds:.1f}s... (speak now)")
    else:
        typer.echo("Recording... (speak now, press Enter to stop)")

    async with AudioCaptureSession(audio_config) as session:
        await session.start()

        stop_event = asyncio.Event()
        meter_task = asyncio.create_task(_meter_loop(session, stop_event))

        if seconds is not None:
            await asyncio.sleep(seconds)
            stop_event.set()
        else:
            await _wait_for_enter(stop_event)

        stop_event.set()
        meter_task.cancel()
        try:
            await meter_task
        except asyncio.CancelledError:
            pass

        sys.stdout.write("\n")
        sys.stdout.flush()

        pcm = await session.stop()
        stats = session.stats()

    typer.echo(
        f"Stopped. {stats.duration_seconds:.1f}s, {stats.chunk_count} chunks, "
        f"peak {stats.peak_dbfs:.0f} dBFS, device: {stats.device_name}"
    )

    if no_save or (not save_last_recording and save_path is None):
        return

    output = save_path or default_recording_path()
    save_wav(output, pcm)
    typer.echo(f"Saved: {output}")


async def _wait_for_enter(stop_event: asyncio.Event) -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, sys.stdin.readline)
    stop_event.set()


async def _meter_loop(
    session: AudioCaptureSession,
    stop_event: asyncio.Event,
) -> None:
    bar_width = 24
    while not stop_event.is_set():
        level = session.current_level
        dbfs = session.current_dbfs
        filled = min(bar_width, int(level * bar_width))
        bar = "#" * filled + "-" * (bar_width - filled)
        line = f"\rLevel: [{bar}] {dbfs:5.0f} dBFS"
        sys.stdout.write(line)
        sys.stdout.flush()
        await asyncio.sleep(0.03)


def register(app: typer.Typer) -> None:
    app.add_typer(audio_app, name="audio")
