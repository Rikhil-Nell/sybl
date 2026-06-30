"""`sybl providers` — list STT providers and capabilities."""

from __future__ import annotations

import json

import typer

from sybl.providers import all_capabilities, list_providers
from sybl.secrets import get_provider_key


def build_providers_payload() -> dict:
    registered = set(list_providers())
    providers: list[dict] = []
    for caps in all_capabilities():
        if caps.name not in registered:
            continue
        providers.append(
            {
                "name": caps.name,
                "streaming": caps.streaming,
                "partial_results": caps.partial_results,
                "requires_key": caps.requires_key,
                "key_configured": bool(get_provider_key(caps.name)),
            }
        )
    return {"providers": providers}


def register(app: typer.Typer) -> None:
    @app.command("providers", rich_help_panel="Configuration")
    def providers_command(
        json_output: bool = typer.Option(
            False,
            "--json",
            help="Emit machine-readable JSON.",
        ),
    ) -> None:
        """List STT providers, capabilities, and key configuration status."""
        payload = build_providers_payload()
        if json_output:
            typer.echo(json.dumps(payload, indent=2))
            return

        if not payload["providers"]:
            typer.echo("No providers registered.")
            return

        typer.echo(f"{'PROVIDER':<12} {'STREAM':<8} {'PARTIALS':<10} KEY")
        typer.echo("-" * 44)
        for item in payload["providers"]:
            stream = "yes" if item["streaming"] else "no"
            partials = "yes" if item["partial_results"] else "no"
            key = "configured" if item["key_configured"] else "missing"
            typer.echo(
                f"{item['name']:<12} {stream:<8} {partials:<10} {key}"
            )
