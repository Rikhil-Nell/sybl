"""`navi start` — daemon with global hotkey dictation."""

from __future__ import annotations

import asyncio
import logging
import signal
import sys

import typer

from navi import __version__
from navi.config import ConfigManager, log_path
from navi.core.dictation import DictationController
from navi.hotkeys import create_hotkey_manager
from navi.logging import setup_logging
from navi.secrets import list_configured_providers

logger = logging.getLogger("navi.start")


def register(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
    ) -> None:
        """Start the Navi daemon with global push-to-talk dictation."""
        verbose = bool(ctx.obj and ctx.obj.get("verbose"))
        config_manager = ConfigManager()
        config = config_manager.load()
        setup_logging(config.logging, log_file=log_path(), verbose=verbose)

        configured = list_configured_providers()
        typer.echo(f"Navi v{__version__}")
        typer.echo(f"Config: {config_manager.path}")
        typer.echo(f"Log file: {log_path()}")
        providers_msg = (
            ", ".join(configured)
            if configured
            else "(none — use `navi config set-key`)"
        )
        typer.echo(f"Configured providers: {providers_msg}")
        typer.echo(
            f"Hotkey: {config.hotkey.binding} ({config.hotkey.mode}) — "
            "hold to dictate, release to transcribe"
        )
        typer.echo(f"Cancel: {config.hotkey.cancel_binding}")
        if config.inject.enabled:
            typer.echo(
                f"Injection: {config.inject.strategy} "
                "(transcript pasted into the focused app on release)"
            )
        else:
            typer.echo("Injection: disabled (transcripts logged only)")
        typer.echo("Press Ctrl+C to stop.")

        if sys.platform != "win32":
            typer.echo(
                "Warning: hotkeys and text injection are Windows-only for now.",
                err=True,
            )

        try:
            asyncio.run(_run_daemon(config, verbose=verbose))
        except NotImplementedError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc


async def _run_daemon(config, *, verbose: bool) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        logger.info("Shutdown requested")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            signal.signal(sig, lambda _signum, _frame: _request_stop())

    controller = DictationController(config, verbose=verbose)
    hotkeys = create_hotkey_manager(config.hotkey)

    await hotkeys.start(controller.handle_hotkey_event)
    logger.info("Navi daemon started")

    try:
        await stop_event.wait()
    finally:
        await controller.shutdown()
        await hotkeys.stop()
        logger.info("Navi daemon stopped")
