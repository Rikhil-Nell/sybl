"""`sybl config` subcommands."""

from __future__ import annotations

import asyncio
import json

import typer

from sybl.cli import exit_codes
from sybl.cli.interactive import is_interactive
from sybl.cli.wizard import pick_provider, prompt_api_key
from sybl.config import ConfigError, ConfigManager
from sybl.config.access import (
    dotted_to_patch,
    get_dotted,
    parse_config_value,
    set_dotted,
)
from sybl.config.edit import EditorError, ensure_config_file, open_in_editor
from sybl.config.sounds import ensure_sounds_layout
from sybl.config.vocabulary import VocabularyError, VocabularyStore
from sybl.ipc.client import IpcClient, IpcConnectionError, is_daemon_running
from sybl.secrets import (
    PROVIDER_KEYS,
    SecretsError,
    list_configured_providers,
    set_provider_key,
)

config_app = typer.Typer(
    help="View and manage sybl configuration.",
    rich_help_panel="Configuration",
)
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
        raise typer.Exit(code=exit_codes.CONFIG_ERROR)

    config = manager.init()
    sounds_path = ensure_sounds_layout()
    typer.echo(f"Created default config at {manager.path}")
    typer.echo(f"Sound cues folder: {sounds_path}")
    typer.echo("Drop start.wav and stop.wav there, or import from TUI Settings.")
    typer.echo(config.model_dump_json(indent=2))


@config_app.command("show")
def config_show_command(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON.",
    ),
) -> None:
    """Show the effective configuration (secrets are never stored here)."""
    payload: dict
    if is_daemon_running():
        try:
            payload = asyncio.run(_fetch_daemon_config())
        except IpcConnectionError:
            payload = {}
        else:
            config_data = payload.get("config", {})
            if json_output:
                typer.echo(json.dumps(config_data, indent=2))
            else:
                typer.echo(json.dumps(config_data, indent=2))
            return

    manager = ConfigManager()
    config = manager.load()
    if json_output:
        typer.echo(config.model_dump_json(indent=2))
    else:
        typer.echo(config.model_dump_json(indent=2))


@config_app.command("get")
def config_get_command(
    path: str = typer.Argument(..., help="Dotted config path."),
) -> None:
    """Read a single config value by dotted path."""
    manager = ConfigManager()
    try:
        config = manager.load()
        value = get_dotted(config, path)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exit_codes.CONFIG_ERROR) from exc

    if isinstance(value, (dict, list)):
        typer.echo(json.dumps(value))
    else:
        typer.echo(value)


@config_app.command("set")
def config_set_command(
    path: str = typer.Argument(..., help="Dotted config path."),
    value: str = typer.Argument(..., help="New value (JSON/bool/number/string)."),
) -> None:
    """Set a config value by dotted path."""
    manager = ConfigManager()
    try:
        config = manager.load()
        updated = set_dotted(config, path, value)
    except ConfigError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exit_codes.CONFIG_ERROR) from exc

    if is_daemon_running():
        try:
            parsed = parse_config_value(value)
            patch = dotted_to_patch(path, parsed)
            asyncio.run(_patch_daemon_config(patch))
        except (ConfigError, IpcConnectionError) as exc:
            msg = str(exc)
            if "validation error" in msg.lower():
                msg += (
                    "\nThe running daemon may be on an older build — "
                    "run `sybl restart` and try again."
                )
            typer.echo(msg, err=True)
            raise typer.Exit(code=exit_codes.CONFIG_ERROR) from exc
        typer.echo(f"Updated {path!r} on the running daemon.")
        return

    manager.save(updated)
    typer.echo(f"Updated {path!r} in {manager.path}.")


@config_app.command("edit")
def config_edit_command() -> None:
    """Open the config file in your editor ($VISUAL/$EDITOR), then reload."""
    path = ensure_config_file()
    try:
        open_in_editor(path)
    except EditorError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exit_codes.GENERAL_ERROR) from exc

    if not is_daemon_running():
        typer.echo(f"Saved {path}.")
        return

    try:
        asyncio.run(_reload_daemon_config())
    except ConfigError as exc:
        typer.echo(f"Saved {path}, but it is invalid: {exc}", err=True)
        typer.echo("Fix the file and re-run `sybl config edit`.", err=True)
        raise typer.Exit(code=exit_codes.CONFIG_ERROR) from exc
    except IpcConnectionError as exc:
        typer.echo(f"Saved {path}, but the daemon could not reload it: {exc}", err=True)
        typer.echo("Restart with `sybl stop && sybl start` to apply.", err=True)
        raise typer.Exit(code=exit_codes.IPC_ERROR) from exc
    typer.echo(f"Saved {path} and reloaded the running daemon.")


@config_app.command("set-key")
def config_set_key_command(
    ctx: typer.Context,
    provider: str | None = typer.Argument(
        None,
        help=f"One of: {', '.join(PROVIDER_KEYS)}",
    ),
) -> None:
    """Securely store a provider API key in the OS keyring."""
    if provider is None:
        if not is_interactive(ctx):
            typer.echo(
                "Provider required in non-interactive mode. "
                f"Usage: sybl config set-key <{'|'.join(PROVIDER_KEYS)}>",
                err=True,
            )
            raise typer.Exit(code=exit_codes.USAGE_ERROR)
        provider = pick_provider(message="Provider for API key")
        if provider is None:
            raise typer.Exit(code=exit_codes.USAGE_ERROR)

    if is_interactive(ctx):
        api_key = prompt_api_key(provider)
        if not api_key:
            raise typer.Exit(code=exit_codes.USAGE_ERROR)
    else:
        typer.echo(
            "Cannot prompt for an API key with --no-input. "
            "Pass the provider and supply the key via your script's secret store.",
            err=True,
        )
        raise typer.Exit(code=exit_codes.USAGE_ERROR)

    try:
        if is_daemon_running():
            asyncio.run(_set_key_via_daemon(provider, api_key))
        else:
            set_provider_key(provider, api_key)
    except (SecretsError, IpcConnectionError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=exit_codes.SECRETS_ERROR) from exc

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
        raise typer.Exit(code=exit_codes.CONFIG_ERROR) from exc
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
        raise typer.Exit(code=exit_codes.CONFIG_ERROR) from exc
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
        raise typer.Exit(code=exit_codes.CONFIG_ERROR) from exc
    typer.echo(f"Removed {term!r}. {len(terms)} term(s) remain.")


def register(app: typer.Typer) -> None:
    app.add_typer(config_app, name="config", rich_help_panel="Configuration")


async def _fetch_daemon_config() -> dict:
    client = IpcClient()
    return await client.get_config()


async def _reload_daemon_config() -> None:
    config = ConfigManager().load()
    client = IpcClient()
    await client.patch_config(config.model_dump(mode="json"))


async def _patch_daemon_config(patch: dict) -> None:
    client = IpcClient()
    await client.patch_config(patch)


async def _set_key_via_daemon(provider: str, api_key: str) -> None:
    client = IpcClient()
    await client.set_provider_key(provider, api_key)
