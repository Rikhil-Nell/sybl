"""`navi transcribe` — record and transcribe via BYOK STT."""

from __future__ import annotations

import asyncio
import sys
from dataclasses import replace

import typer

from navi.audio import AudioCaptureSession, AudioError
from navi.cli.meter import meter_loop, wait_for_enter
from navi.config import ConfigManager, log_path
from navi.core.transcribe import transcribe_pcm, transcribe_stream
from navi.logging import setup_logging
from navi.providers import STTError, resolve_provider

transcribe_app = typer.Typer(help="Record and transcribe speech.")


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
    stream: bool = typer.Option(
        False,
        "--stream",
        help="Stream audio to a streaming provider and show live partials.",
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
        asyncio.run(_transcribe(navi_config, seconds, device, provider, stream))
    except AudioError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    except STTError as exc:
        sys.stdout.write("\n")
        sys.stdout.flush()
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


async def _transcribe(
    navi_config,
    seconds: float | None,
    device: str | None,
    provider: str | None,
    stream: bool,
) -> None:
    audio_config = navi_config.audio.model_copy(
        update={"device": device if device is not None else navi_config.audio.device}
    )

    if seconds is not None:
        typer.echo(f"Recording for {seconds:.1f}s... (speak now)")
    else:
        typer.echo("Recording... (speak now, press Enter to stop)")

    stream_provider_id: str | None = None
    stream_provider = None
    if stream:
        stream_provider_id, stream_provider = resolve_provider(
            navi_config,
            prefer=provider,
            streaming_required=True,
        )

    async with AudioCaptureSession(audio_config) as session:
        await session.start()

        stop_event = asyncio.Event()
        meter_task = asyncio.create_task(meter_loop(session, stop_event))

        if stream:
            partial_line = ["Partial: "]

            def on_partial(text: str) -> None:
                partial_line[0] = f"Partial: {text}"
                sys.stdout.write(f"\r{partial_line[0]:<80}")
                sys.stdout.flush()

            stream_task = asyncio.create_task(
                transcribe_stream(
                    navi_config,
                    session,
                    provider_id=stream_provider_id,
                    provider=stream_provider,
                    on_partial=on_partial,
                )
            )
        else:
            stream_task = None

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

        if stream_task is not None:
            if stream_task.done() and stream_task.exception() is not None:
                await stream_task
            outcome = await stream_task
            outcome = replace(
                outcome,
                audio_duration_seconds=stats.duration_seconds,
                peak_dbfs=stats.peak_dbfs,
            )
        else:
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
