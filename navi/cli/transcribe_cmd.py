"""`navi transcribe` — record and transcribe via BYOK STT."""

from __future__ import annotations

import asyncio
import sys

import typer

from navi.audio import AudioCaptureSession, AudioError
from navi.cli.meter import meter_loop, wait_for_enter
from navi.config import ConfigManager, log_path
from navi.core.transcribe import transcribe_pcm
from navi.logging import setup_logging
from navi.providers import STTError

transcribe_app = typer.Typer(help="Record and transcribe speech (Phase 2).")


@transcribe_app.callback(invoke_without_command=True)
def transcribe_command(
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
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Override STT provider (default: config preferred).",
    ),
) -> None:
    """Record from the microphone and transcribe via your configured STT provider."""
    if ctx.invoked_subcommand is not None:
        return

    verbose = bool(ctx.obj and ctx.obj.get("verbose"))
    config_manager = ConfigManager()
    navi_config = config_manager.load()
    setup_logging(navi_config.logging, log_file=log_path(), verbose=verbose)

    try:
        asyncio.run(_transcribe(navi_config, seconds, device, provider))
    except AudioError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except STTError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


async def _transcribe(
    navi_config,
    seconds: float | None,
    device: str | None,
    provider: str | None,
) -> None:
    audio_config = navi_config.audio.model_copy(
        update={"device": device if device is not None else navi_config.audio.device}
    )

    if seconds is not None:
        typer.echo(f"Recording for {seconds:.1f}s... (speak now)")
    else:
        typer.echo("Recording... (speak now, press Enter to stop)")

    async with AudioCaptureSession(audio_config) as session:
        await session.start()

        stop_event = asyncio.Event()
        meter_task = asyncio.create_task(meter_loop(session, stop_event))

        if seconds is not None:
            await asyncio.sleep(seconds)
            stop_event.set()
        else:
            await wait_for_enter(stop_event)

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

    outcome = await transcribe_pcm(
        navi_config,
        pcm,
        provider_name=provider,
        audio_duration_seconds=stats.duration_seconds,
        peak_dbfs=stats.peak_dbfs,
    )

    typer.echo(f'Transcript: "{outcome.text}"')
    model_label = outcome.model or "unknown"
    typer.echo(
        f"Provider: {outcome.provider} ({model_label}) | "
        f"Audio: {outcome.audio_duration_seconds:.1f}s | "
        f"Latency: {outcome.latency_seconds:.1f}s"
    )


def register(app: typer.Typer) -> None:
    app.add_typer(transcribe_app, name="transcribe")
