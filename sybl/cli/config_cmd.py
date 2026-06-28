"""`sybl config` subcommands."""

from __future__ import annotations

import asyncio

import typer

from sybl.config import ConfigManager
from sybl.config.vocabulary import VocabularyError, VocabularyStore
from sybl.ipc.client import IpcClient, IpcConnectionError, is_daemon_running
from sybl.secrets import (
    PROVIDER_KEYS,
    SecretsError,
    list_configured_providers,
    set_provider_key,
)

config_app = typer.Typer(help="View and manage sybl configuration.")
vocab_app = typer.Typer(help="Manage STT vocabulary hints.")
config_app.add_typer(vocab_app, name="vocab")


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
    if is_daemon_running():
        try:
            payload = asyncio.run(_fetch_daemon_config())
        except IpcConnectionError:
            pass
        else:
            import json

            typer.echo(json.dumps(payload.get("config", {}), indent=2))
            return

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
        if is_daemon_running():
            asyncio.run(_set_key_via_daemon(provider, api_key))
        else:
            set_provider_key(provider, api_key)
    except (SecretsError, IpcConnectionError) as exc:
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


@vocab_app.command("path")
def vocab_path_command() -> None:
    """Print the vocabulary file path."""
    store = VocabularyStore()
    typer.echo(store.path)


@vocab_app.command("list")
def vocab_list_command() -> None:
    """List configured STT vocabulary hints."""
    store = VocabularyStore()
    try:
        terms = store.load_terms()
    except VocabularyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    if not terms:
        typer.echo("No vocabulary terms configured.")
        typer.echo("Add terms with: sybl config vocab add <term>")
        typer.echo(f"File: {store.path}")
        return
    typer.echo(f"Vocabulary ({store.path}):")
    for term in terms:
        typer.echo(f"  - {term}")


@vocab_app.command("add")
def vocab_add_command(
    term: str = typer.Argument(..., help="Name, jargon term, or proper noun"),
) -> None:
    """Add a vocabulary hint passed to STT providers at session start."""
    store = VocabularyStore()
    try:
        terms = store.add_term(term)
    except VocabularyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Added {term!r}. {len(terms)} term(s) configured.")


@vocab_app.command("remove")
def vocab_remove_command(
    term: str = typer.Argument(..., help="Term to remove"),
) -> None:
    """Remove a vocabulary hint."""
    store = VocabularyStore()
    try:
        terms = store.remove_term(term)
    except VocabularyError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc
    typer.echo(f"Removed {term!r}. {len(terms)} term(s) remain.")


def register(app: typer.Typer) -> None:
    app.add_typer(config_app, name="config")


async def _fetch_daemon_config() -> dict:
    client = IpcClient()
    return await client.get_config()


async def _set_key_via_daemon(provider: str, api_key: str) -> None:
    client = IpcClient()
    await client.set_provider_key(provider, api_key)
