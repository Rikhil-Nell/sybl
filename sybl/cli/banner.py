"""ASCII banner rendering for the sybl CLI."""

from __future__ import annotations

import asyncio
import sys
from importlib import resources

from rich.console import Console

from sybl.config import ConfigManager
from sybl.ipc.client import IpcClient, is_daemon_running

_BANNER_PACKAGE = "sybl.cli.assets"
_BANNER_FILE = "banner.txt"


def load_banner_text() -> str:
    """Load banner art from the packaged asset file."""
    try:
        asset = resources.files(_BANNER_PACKAGE).joinpath(_BANNER_FILE)
        return asset.read_text(encoding="utf-8").rstrip("\n")
    except (FileNotFoundError, OSError, TypeError):
        return "sybl — open-source BYOK voice dictation"


def render_banner(*, console: Console | None = None, err: bool = False) -> None:
    """Print the ASCII banner with Rich styling."""
    text = load_banner_text()
    target = console or Console(file=sys.stderr if err else sys.stdout)
    target.print(text, style="bold cyan")
    target.print(
        "open-source BYOK voice dictation — speak anywhere, type it in",
        style="dim",
    )


def first_run_shown() -> bool:
    manager = ConfigManager()
    config = manager.load()
    return config.ui.first_run_shown


def mark_first_run_shown() -> None:
    if is_daemon_running():
        asyncio.run(_mark_first_run_via_daemon())
        return
    manager = ConfigManager()
    config = manager.load()
    if config.ui.first_run_shown:
        return
    updated = config.model_copy(
        update={"ui": config.ui.model_copy(update={"first_run_shown": True})}
    )
    manager.save(updated)


async def _mark_first_run_via_daemon() -> None:
    client = IpcClient()
    await client.patch_config({"ui": {"first_run_shown": True}})
