"""`sybl hotkey test` — verify global hotkey bindings."""

from __future__ import annotations

import asyncio
import signal
import sys

import typer

from sybl.config import ConfigManager, log_path
from sybl.hotkeys import HotkeyEvent, create_hotkey_manager
from sybl.logging import setup_logging

hotkey_app = typer.Typer(
    help="Test global hotkey bindings.",
    no_args_is_help=True,
)


@hotkey_app.command("test")
def hotkey_test_command(
    ctx: typer.Context,
) -> None:
    """Print hotkey activate/deactivate/cancel events. Press Ctrl+C to exit."""
    verbose = bool(ctx.obj and ctx.obj.get("verbose"))
    config_manager = ConfigManager()
    config = config_manager.load()
    setup_logging(config.logging, log_file=log_path(), verbose=verbose)

    typer.echo(f"Binding: {config.hotkey.binding} ({config.hotkey.mode})")
    typer.echo(f"Cancel: {config.hotkey.cancel_binding}")
    typer.echo("Hold the binding to see activate/deactivate. Press Esc to cancel.")
    typer.echo("Press Ctrl+C to exit.")

    if sys.platform != "win32":
        typer.echo("Warning: global hotkeys are Windows-only in Phase 4.", err=True)

    try:
        asyncio.run(_run_test(config.hotkey))
    except NotImplementedError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


async def _run_test(hotkey_config) -> None:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        stop_event.set()

    try:
        loop.add_signal_handler(signal.SIGINT, _request_stop)
    except NotImplementedError:
        signal.signal(signal.SIGINT, lambda _s, _f: _request_stop())

    hotkeys = create_hotkey_manager(hotkey_config)

    async def on_event(event: HotkeyEvent) -> None:
        typer.echo(event.value)

    await hotkeys.start(on_event)

    try:
        await stop_event.wait()
    finally:
        await hotkeys.stop()


def register(app: typer.Typer) -> None:
    app.add_typer(hotkey_app, name="hotkey")
