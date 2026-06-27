"""`navi config` subcommands."""

from __future__ import annotations

import typer

from navi.config import ConfigManager
from navi.secrets import (
    PROVIDER_KEYS,
    SecretsError,
    list_configured_providers,
    set_provider_key,
)

config_app = typer.Typer(help="View and manage Navi configuration.")


@config_app.command("path")
def config_path_command() -> None:
    """Print the resolved config file path."""
    manager = ConfigManager()
    typer.echo(manager.path)


@config_app.command("init")
def config_init_command() -> None:
    """Write a default config file."""
    manager = ConfigManager()
    if manager.path.exists():
        typer.echo(f"Config already exists at {manager.path}")
        raise typer.Exit(code=1)

    config = manager.init()
    typer.echo(f"Created default config at {manager.path}")
    typer.echo(config.model_dump_json(indent=2))


@config_app.command("show")
def config_show_command() -> None:
    """Show the effective configuration (secrets are never stored here)."""
    manager = ConfigManager()
    config = manager.load()
    typer.echo(config.model_dump_json(indent=2))


@config_app.command("set-key")
def config_set_key_command(
    provider: str = typer.Argument(..., help=f"One of: {', '.join(PROVIDER_KEYS)}"),
) -> None:
    """Securely store a provider API key in the OS keyring."""
    api_key = typer.prompt(
        f"Enter API key for {provider}",
        hide_input=True,
        confirmation_prompt=True,
    )
    try:
        set_provider_key(provider, api_key)
    except SecretsError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(f"Stored key for {provider} in the OS keyring.")


@config_app.command("keys")
def config_keys_command() -> None:
    """List providers that have API keys configured."""
    configured = list_configured_providers()
    if not configured:
        typer.echo("No provider keys configured.")
        typer.echo(f"Supported providers: {', '.join(PROVIDER_KEYS)}")
        return

    typer.echo("Configured provider keys:")
    for provider in configured:
        typer.echo(f"  - {provider}")


def register(app: typer.Typer) -> None:
    app.add_typer(config_app, name="config")
