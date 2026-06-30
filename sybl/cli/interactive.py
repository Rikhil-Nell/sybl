"""TTY and --no-input gating for interactive CLI flows."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import typer

from sybl.cli.exit_codes import USAGE_ERROR

if TYPE_CHECKING:
    from typer.models import Context


def ctx_no_input(ctx: Context | None) -> bool:
    if ctx is None or ctx.obj is None:
        return False
    return bool(ctx.obj.get("no_input"))


def is_interactive(ctx: Context | None) -> bool:
    if ctx_no_input(ctx):
        return False
    return sys.stdin.isatty() and sys.stdout.isatty()


def require_interactive(ctx: Context | None, *, hint: str) -> None:
    if is_interactive(ctx):
        return
    typer.echo(hint, err=True)
    raise typer.Exit(code=USAGE_ERROR)
