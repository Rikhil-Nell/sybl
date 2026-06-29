"""`sybl start` — daemon with global hotkey dictation."""

from __future__ import annotations

import asyncio
import sys

import typer

from sybl import __version__
from sybl.config import ConfigManager, log_path
from sybl.config.paths import sounds_dir
from sybl.core.daemon import SyblDaemon
from sybl.daemon.spawn import spawn_background_daemon, wait_for_daemon_ready
from sybl.ipc.client import is_daemon_running
from sybl.ipc.single_instance import DaemonAlreadyRunningError
from sybl.secrets import list_configured_providers


def _hotkey_help_lines(config) -> list[str]:
    binding = config.hotkey.binding
    cancel = config.hotkey.cancel_binding
    mode = config.hotkey.mode
    lines: list[str] = [f"Hotkey: {binding} (mode={mode})"]

    if mode in ("ptt", "both"):
        hold = (
            f" after {config.hotkey.ptt_hold_ms}ms"
            if mode == "both"
            else ""
        )
        lines.append(f"  PTT: hold {binding}{hold}, release to finish")
    if mode in ("toggle", "both"):
        window = config.hotkey.toggle_double_press_ms
        lines.append(
            f"  Toggle: double-press {binding} within {window}ms to start; "
            f"press once while listening to stop"
        )
    lines.append(f"  Cancel while listening: {cancel}")
    return lines


def register(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
        foreground: bool = typer.Option(
            False,
            "--foreground",
            "-f",
            help="Run in this terminal (debug). Default starts a background process.",
        ),
    ) -> None:
        """Start the sybl daemon with global push-to-talk dictation."""
        verbose = bool(ctx.obj and ctx.obj.get("verbose"))
        config_manager = ConfigManager()
        config = config_manager.load()

        configured = list_configured_providers()
        typer.echo(f"sybl v{__version__}")
        typer.echo(f"Config: {config_manager.path}")
        typer.echo(f"Log file: {log_path()}")
        typer.echo(f"Sound cues: {sounds_dir()} (start.wav / stop.wav)")
        providers_msg = (
            ", ".join(configured)
            if configured
            else "(none — use `sybl config set-key`)"
        )
        typer.echo(f"Configured providers: {providers_msg}")
        for line in _hotkey_help_lines(config):
            typer.echo(line)
        if config.inject.enabled:
            typer.echo(
                f"Injection: {config.inject.strategy} "
                "(transcript pasted into the focused app when a session ends)"
            )
        else:
            typer.echo("Injection: disabled (transcripts logged only)")

        if sys.platform != "win32":
            typer.echo(
                "Warning: hotkeys and text injection are Windows-only for now.",
                err=True,
            )

        if foreground:
            typer.echo("Attach the TUI from another terminal: sybl tui")
            typer.echo(
                "Press Ctrl+C to stop (or run `sybl stop` from another terminal)."
            )
            try:
                asyncio.run(_run_daemon(verbose=verbose))
            except DaemonAlreadyRunningError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(code=1) from exc
            except NotImplementedError as exc:
                typer.echo(str(exc), err=True)
                raise typer.Exit(code=1) from exc
            return

        try:
            if is_daemon_running():
                typer.echo(
                    "sybl daemon is already running. Use `sybl status` or `sybl stop`.",
                    err=True,
                )
                raise typer.Exit(code=1)
            spawn_background_daemon(verbose=verbose)
            pid = wait_for_daemon_ready()
        except TimeoutError as exc:
            typer.echo(str(exc), err=True)
            typer.echo(f"Check the log file: {log_path()}", err=True)
            raise typer.Exit(code=1) from exc

        typer.echo(f"Daemon running in background (pid={pid}).")
        typer.echo("View logs and settings: sybl tui")
        typer.echo("Stop: sybl stop")


async def _run_daemon(*, verbose: bool) -> None:
    daemon = SyblDaemon(verbose=verbose)
    await daemon.run()
