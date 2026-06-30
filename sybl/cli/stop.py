"""`sybl stop` — shut down the running daemon."""

from __future__ import annotations

import asyncio

import typer

from sybl.cli import exit_codes
from sybl.cli.io import echo_error
from sybl.ipc.client import IpcClient, IpcConnectionError, is_daemon_running


def register(app: typer.Typer) -> None:
    @app.command("stop", rich_help_panel="Daemon")
    def stop_command() -> None:
        """Gracefully stop the sybl daemon."""
        if not is_daemon_running():
            echo_error("sybl daemon is not running.")
            raise typer.Exit(code=exit_codes.DAEMON_NOT_RUNNING)

        try:
            asyncio.run(_stop_daemon())
        except IpcConnectionError as exc:
            echo_error(str(exc))
            raise typer.Exit(code=exit_codes.IPC_ERROR) from exc

        typer.echo("Shutdown requested.")


async def _stop_daemon() -> None:
    client = IpcClient()
    await client.shutdown()
