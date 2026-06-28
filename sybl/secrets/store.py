"""OS keyring wrapper for BYOK provider API keys."""

from __future__ import annotations

import keyring
import keyring.errors

SERVICE_NAME = "sybl"
PROVIDER_KEYS = ("groq", "deepgram", "assemblyai", "gladia")


class SecretsError(Exception):
    """Raised when secret storage operations fail."""


def _username(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in PROVIDER_KEYS:
        supported = ", ".join(PROVIDER_KEYS)
        raise SecretsError(f"Unknown provider {provider!r}. Supported: {supported}")
    return f"{normalized}_api_key"


def set_provider_key(provider: str, key: str) -> None:
    try:
        keyring.set_password(SERVICE_NAME, _username(provider), key)
    except keyring.errors.KeyringError as exc:
        raise SecretsError(f"Failed to store key for {provider}: {exc}") from exc


def get_provider_key(provider: str) -> str | None:
    try:
        return keyring.get_password(SERVICE_NAME, _username(provider))
    except keyring.errors.KeyringError as exc:
        raise SecretsError(f"Failed to read key for {provider}: {exc}") from exc


def delete_provider_key(provider: str) -> None:
    try:
        keyring.delete_password(SERVICE_NAME, _username(provider))
    except keyring.errors.PasswordDeleteError:
        return
    except keyring.errors.KeyringError as exc:
        raise SecretsError(f"Failed to delete key for {provider}: {exc}") from exc


def list_configured_providers() -> list[str]:
    configured: list[str] = []
    for provider in PROVIDER_KEYS:
        if get_provider_key(provider):
            configured.append(provider)
    return configured
