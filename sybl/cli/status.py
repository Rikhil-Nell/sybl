"""`sybl status` — query the running daemon."""

from __future__ import annotations

import asyncio
import json

import typer

from sybl.cli import exit_codes
from sybl.cli.io import echo_error
from sybl.ipc.client import IpcClient, IpcConnectionError, is_daemon_running


def register(app: typer.Typer) -> None:
    @app.command("status", rich_help_panel="Daemon")
    def status_command(
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable JSON.",
        ),
    ) -> None:
        """Show daemon status (state, provider, hotkey)."""
        if not is_daemon_running():
            echo_error("sybl daemon is not running.")
            raise typer.Exit(code=exit_codes.DAEMON_NOT_RUNNING)

        try:
            status = asyncio.run(_fetch_status())
        except IpcConnectionError as exc:
            echo_error(str(exc))
            raise typer.Exit(code=exit_codes.IPC_ERROR) from exc

        if json_output:
            typer.echo(json.dumps(status, indent=2))
            return

        typer.echo(f"State: {status.get('state', 'unknown')}")
        typer.echo(f"Provider: {status.get('provider', 'unknown')}")
        typer.echo(f"Hotkey: {status.get('hotkey_binding', 'unknown')}")
        typer.echo(f"Audio device: {status.get('audio_device', 'default')}")
        typer.echo(f"Version: {status.get('version', 'unknown')}")
        uptime = status.get("uptime_seconds")
        if uptime is not None:
            typer.echo(f"Uptime: {float(uptime):.0f}s")


async def _fetch_status() -> dict:
    client = IpcClient()
    return await client.get_status()
