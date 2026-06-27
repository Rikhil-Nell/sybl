"""`navi tui` — stub until Phase 7."""

import typer

from navi.config import log_path


def register(app: typer.Typer) -> None:
    @app.command("tui")
    def tui_command() -> None:
        """Attach to the Navi TUI (Phase 7 — not yet implemented)."""
        typer.echo("The Textual TUI arrives in Phase 7.")
        typer.echo("For now, tail the daemon log file:")
        typer.echo(f"  Get-Content -Wait {log_path()}")
