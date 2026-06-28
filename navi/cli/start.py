"""`navi start` — daemon with global hotkey dictation."""

from __future__ import annotations

import asyncio
import sys

import typer

from navi import __version__
from navi.config import ConfigManager, log_path
from navi.core.daemon import NaviDaemon
from navi.ipc.single_instance import DaemonAlreadyRunningError
from navi.secrets import list_configured_providers


def register(app: typer.Typer) -> None:
    @app.command("start")
    def start_command(
        ctx: typer.Context,
    ) -> None:
        """Start the Navi daemon with global push-to-talk dictation."""
        verbose = bool(ctx.obj and ctx.obj.get("verbose"))
        config_manager = ConfigManager()
        config = config_manager.load()

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
        typer.echo("Attach the TUI from another terminal: navi tui")
        typer.echo("Press Ctrl+C to stop (or run `navi stop` from another terminal).")

        if sys.platform != "win32":
            typer.echo(
                "Warning: hotkeys and text injection are Windows-only for now.",
                err=True,
            )

        try:
            asyncio.run(_run_daemon(verbose=verbose))
        except DaemonAlreadyRunningError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        except NotImplementedError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc


async def _run_daemon(*, verbose: bool) -> None:
    daemon = NaviDaemon(verbose=verbose)
    await daemon.run()
