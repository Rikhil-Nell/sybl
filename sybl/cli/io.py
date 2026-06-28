"""CLI output helpers."""

from __future__ import annotations

import typer


def echo_error(message: str) -> None:
    """Write an error message, falling back to stdout if stderr is unavailable."""
    try:
        typer.echo(message, err=True)
    except OSError:
        typer.echo(message)
