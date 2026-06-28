"""`navi tui` — attach to the running daemon."""

from __future__ import annotations

import typer

from navi.cli.io import echo_error
from navi.ipc.client import IpcConnectionError, is_daemon_running


def register(app: typer.Typer) -> None:
    @app.command("tui")
    def tui_command() -> None:
        """Attach to the Navi TUI (logs, status, history)."""
        if not is_daemon_running():
            echo_error(
                "Navi daemon is not running. Start it with `navi start`.",
            )
            raise typer.Exit(code=1)

        try:
            from navi.tui.app import run_tui

            run_tui()
        except IpcConnectionError as exc:
            echo_error(str(exc))
            raise typer.Exit(code=1) from exc
        except ImportError as exc:
            echo_error(f"Textual TUI unavailable: {exc}")
            raise typer.Exit(code=1) from exc
