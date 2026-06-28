"""`navi stop` — shut down the running daemon."""

from __future__ import annotations

import asyncio

import typer

from navi.cli.io import echo_error
from navi.ipc.client import IpcClient, IpcConnectionError, is_daemon_running


def register(app: typer.Typer) -> None:
    @app.command("stop")
    def stop_command() -> None:
        """Gracefully stop the Navi daemon."""
        if not is_daemon_running():
            echo_error("Navi daemon is not running.")
            raise typer.Exit(code=1)

        try:
            asyncio.run(_stop_daemon())
        except IpcConnectionError as exc:
            echo_error(str(exc))
            raise typer.Exit(code=1) from exc

        typer.echo("Shutdown requested.")


async def _stop_daemon() -> None:
    client = IpcClient()
    await client.shutdown()
