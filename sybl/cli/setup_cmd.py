"""`sybl setup` — first-run interactive wizard."""

from __future__ import annotations

import asyncio

import typer

from sybl.cli import exit_codes
from sybl.cli.interactive import require_interactive
from sybl.cli.wizard import (
    confirm_mic_smoke,
    pick_hotkey_mode,
    pick_provider,
    prompt_api_key,
)
from sybl.config import ConfigManager
from sybl.config.sounds import ensure_sounds_layout
from sybl.ipc.client import IpcClient, IpcConnectionError, is_daemon_running
from sybl.secrets import SecretsError, set_provider_key


def register(app: typer.Typer) -> None:
    @app.command("setup", rich_help_panel="Configuration")
    def setup_command(ctx: typer.Context) -> None:
        """Interactive first-run setup (provider, API key, mic, hotkey mode)."""
        require_interactive(
            ctx,
            hint=(
                "Interactive setup requires a TTY. "
                "Use `sybl config set-key <provider>` and `sybl config set` instead, "
                "or omit `--no-input`."
            ),
        )

        manager = ConfigManager()
        if not manager.path.exists():
            manager.init()
        config = manager.load()

        typer.echo("Welcome to sybl setup.")
        provider = pick_provider()
        if provider is None:
            raise typer.Exit(code=exit_codes.USAGE_ERROR)

        api_key = prompt_api_key(provider)
        if not api_key:
            raise typer.Exit(code=exit_codes.USAGE_ERROR)

        mode = pick_hotkey_mode()
        if mode is None:
            raise typer.Exit(code=exit_codes.USAGE_ERROR)

        if confirm_mic_smoke():
            from sybl.cli.doctor import _check_mic_smoke

            results = _check_mic_smoke()
            for result in results:
                typer.echo(f"[{result.status.value}] {result.name}: {result.detail}")

        updated = config.model_copy(
            update={
                "provider": config.provider.model_copy(update={"preferred": provider}),
                "hotkey": config.hotkey.model_copy(update={"mode": mode}),
                "ui": config.ui.model_copy(
                    update={
                        "onboarding_complete": True,
                        "first_run_shown": True,
                    }
                ),
            }
        )

        try:
            if is_daemon_running():
                asyncio.run(_apply_setup_via_daemon(updated, provider, api_key))
            else:
                set_provider_key(provider, api_key)
                manager.save(updated)
        except (SecretsError, IpcConnectionError) as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=exit_codes.SECRETS_ERROR) from exc

        ensure_sounds_layout()
        typer.echo("Setup complete.")
        typer.echo(f"Preferred provider: {provider}")
        typer.echo(f"Hotkey mode: {mode}")
        typer.echo("Start the daemon with: sybl start")


async def _apply_setup_via_daemon(config, provider: str, api_key: str) -> None:
    client = IpcClient()
    await client.set_provider_key(provider, api_key)
    await client.patch_config(config.model_dump(mode="json"))
