"""sybl CLI entrypoint."""

from __future__ import annotations

import typer

from sybl.cli import (
    audio_cmd,
    config_cmd,
    doctor,
    hotkey_cmd,
    start,
    status,
    stop,
    transcribe_cmd,
    tui,
)

app = typer.Typer(
    name="sybl",
    help="sybl — open-source BYOK voice dictation.",
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
status.register(app)
stop.register(app)
tui.register(app)
config_cmd.register(app)
audio_cmd.register(app)
transcribe_cmd.register(app)
hotkey_cmd.register(app)
doctor.register(app)


def _entrypoint() -> None:
    app()


if __name__ == "__main__":
    _entrypoint()
