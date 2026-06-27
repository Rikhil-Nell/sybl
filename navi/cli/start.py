"""`navi start` — minimal daemon skeleton."""

from __future__ import annotations

import asyncio
import logging
import signal

import typer

from navi import __version__
from navi.config import ConfigManager, log_path
from navi.logging import setup_logging
from navi.secrets import list_configured_providers

logger = logging.getLogger("navi.start")


def register(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
    ) -> None:
        """Start the Navi daemon (skeleton — hotkeys/audio arrive in later phases)."""
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
        typer.echo("Daemon skeleton running. Press Ctrl+C to stop.")

        asyncio.run(_run_daemon())


async def _run_daemon() -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        logger.info("Shutdown requested")
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            # Windows ProactorEventLoop does not support add_signal_handler.
            signal.signal(sig, lambda _signum, _frame: _request_stop())

    logger.info("Navi daemon started")

    while not stop_event.is_set():
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=30.0)
        except TimeoutError:
            logger.info("Heartbeat — daemon idle (Phase 0 skeleton)")

    logger.info("Navi daemon stopped")
