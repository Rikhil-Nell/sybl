"""Navi CLI entrypoint."""

from __future__ import annotations

import typer

from navi.cli import audio_cmd, config_cmd, doctor, start, tui

app = typer.Typer(
    name="navi",
    help="Navi — open-source BYOK voice dictation.",
    no_args_is_help=True,
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
) -> None:
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose


start.register(app)
tui.register(app)
config_cmd.register(app)
audio_cmd.register(app)
doctor.register(app)


def _entrypoint() -> None:
    app()


if __name__ == "__main__":
    _entrypoint()
