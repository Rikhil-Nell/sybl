"""`sybl restart` — stop and start the daemon."""

from __future__ import annotations

import asyncio
import time

import typer

from sybl.cli import exit_codes
from sybl.cli.io import echo_error
from sybl.cli.stop import _stop_daemon
from sybl.daemon.spawn import spawn_background_daemon, wait_for_daemon_ready
from sybl.ipc.client import IpcConnectionError, is_daemon_running


def register(app: typer.Typer) -> None:
    @app.command("restart", rich_help_panel="Daemon")
    def restart_command(ctx: typer.Context) -> None:
        """Stop the running daemon (if any) and start it again."""
        if is_daemon_running():
            try:
                asyncio.run(_stop_daemon())
            except IpcConnectionError as exc:
                echo_error(str(exc))
                raise typer.Exit(code=exit_codes.IPC_ERROR) from exc
            typer.echo("Shutdown requested.")
            _wait_for_daemon_stop()

        try:
            if is_daemon_running():
                echo_error("sybl daemon is still running after stop.")
                raise typer.Exit(code=exit_codes.IPC_ERROR)
            spawn_background_daemon(verbose=bool(ctx.obj and ctx.obj.get("verbose")))
            pid = wait_for_daemon_ready()
        except TimeoutError as exc:
            echo_error(str(exc))
            raise typer.Exit(code=exit_codes.GENERAL_ERROR) from exc

        typer.echo(f"Daemon restarted (pid={pid}).")


def _wait_for_daemon_stop(*, timeout: float = 10.0, interval: float = 0.2) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not is_daemon_running():
            return
        time.sleep(interval)
