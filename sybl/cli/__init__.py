"""sybl CLI entrypoint."""

from __future__ import annotations

import typer
from typer.core import TyperGroup

from sybl.cli import (
    audio_cmd,
    config_cmd,
    doctor,
    hotkey_cmd,
    indicator_cmd,
    logs,
    providers_cmd,
    restart,
    setup_cmd,
    start,
    status,
    stop,
    transcribe_cmd,
    tui,
)
from sybl.cli.banner import first_run_shown, mark_first_run_shown, render_banner


class SyblGroup(TyperGroup):
    """Typer group that renders the sybl banner above help text."""

    def format_help(self, ctx, formatter) -> None:
        if self.rich_markup_mode is None:
            render_banner()
            return super().format_help(ctx, formatter)
        from typer import rich_utils

        render_banner()
        return rich_utils.rich_format_help(
            obj=self,
            ctx=ctx,
            markup_mode=self.rich_markup_mode,
        )


app = typer.Typer(
    name="sybl",
    help="sybl — open-source BYOK voice dictation.",
    cls=SyblGroup,
    rich_markup_mode="rich",
    invoke_without_command=True,
)


@app.callback()
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(
        False,
        "--verbose",
        "-v",
        help="Enable debug logging for commands that support it.",
    ),
    no_input: bool = typer.Option(
        False,
        "--no-input",
        help="Disable interactive prompts and wizards (for scripts/agents).",
    ),
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["no_input"] = no_input

    bare = ctx.invoked_subcommand is None
    if bare:
        if not first_run_shown():
            mark_first_run_shown()
        typer.echo(ctx.get_help())
        raise typer.Exit()

    if not first_run_shown():
        render_banner(err=True)
        mark_first_run_shown()


start.register(app)
status.register(app)
stop.register(app)
restart.register(app)
logs.register(app)
tui.register(app)
config_cmd.register(app)
setup_cmd.register(app)
providers_cmd.register(app)
audio_cmd.register(app)
transcribe_cmd.register(app)
hotkey_cmd.register(app)
indicator_cmd.register(app)
doctor.register(app)


def _entrypoint() -> None:
    app()


if __name__ == "__main__":
    _entrypoint()
