"""`sybl tui` — attach to the running daemon."""

from __future__ import annotations

import typer

from sybl.cli.io import echo_error
from sybl.ipc.client import IpcConnectionError, is_daemon_running


def register(app: typer.Typer) -> None:
    @app.command("tui")
    def tui_command(
        demo: bool = typer.Option(
            False,
            "--demo",
            help="Run with scripted sample data — no daemon required (for "
            "screenshots and quick UI previews).",
        ),
    ) -> None:
        """Attach to the sybl TUI (logs, status, history)."""
        if not demo and not is_daemon_running():
            echo_error(
                "sybl daemon is not running. Start it with `sybl start`, "
                "or preview the UI with `sybl tui --demo`.",
            )
            raise typer.Exit(code=1)

        try:
            from sybl.tui.app import run_tui

            run_tui(demo=demo)
        except IpcConnectionError as exc:
            echo_error(str(exc))
            raise typer.Exit(code=1) from exc
        except ImportError as exc:
            echo_error(f"Textual TUI unavailable: {exc}")
            raise typer.Exit(code=1) from exc
