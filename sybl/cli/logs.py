"""`sybl logs` — tail the daemon log file."""

from __future__ import annotations

import sys
import time

import typer

from sybl.cli import exit_codes
from sybl.cli.io import echo_error
from sybl.config import log_path


def register(app: typer.Typer) -> None:
    @app.command("logs", rich_help_panel="Daemon")
    def logs_command(
        follow: bool = typer.Option(
            False,
            "--follow",
            "-f",
            help="Keep streaming new log lines.",
        ),
        lines: int = typer.Option(
            50,
            "--lines",
            "-n",
            min=1,
            help="Number of recent lines to show.",
        ),
    ) -> None:
        """Tail the daemon log file."""
        path = log_path()
        if not path.exists():
            echo_error(f"Log file not found: {path}")
            raise typer.Exit(code=exit_codes.GENERAL_ERROR)

        content = path.read_text(encoding="utf-8", errors="replace")
        all_lines = content.splitlines()
        tail = all_lines[-lines:] if lines < len(all_lines) else all_lines
        for line in tail:
            typer.echo(line)

        if not follow:
            return

        if not sys.stdout.isatty():
            echo_error("--follow requires a TTY.")
            raise typer.Exit(code=exit_codes.USAGE_ERROR)

        _follow_file(path, start_size=path.stat().st_size)


def _follow_file(path, *, start_size: int) -> None:
    offset = start_size
    try:
        while True:
            size = path.stat().st_size
            if size > offset:
                with path.open("r", encoding="utf-8", errors="replace") as handle:
                    handle.seek(offset)
                    chunk = handle.read()
                    if chunk:
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    offset = handle.tell()
            elif size < offset:
                offset = 0
            time.sleep(0.25)
    except KeyboardInterrupt:
        typer.echo()
