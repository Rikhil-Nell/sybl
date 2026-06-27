"""Tests for keyring-backed secret storage."""

from unittest.mock import patch

import pytest

from navi.secrets import (
    SecretsError,
    delete_provider_key,
    get_provider_key,
    list_configured_providers,
    set_provider_key,
)


@pytest.fixture
def fake_keyring() -> dict[tuple[str, str], str]:
    return {}


@pytest.fixture
def keyring_backend(fake_keyring: dict[tuple[str, str], str]):
    def set_password(service: str, username: str, password: str) -> None:
        fake_keyring[(service, username)] = password

    def get_password(service: str, username: str) -> str | None:
        return fake_keyring.get((service, username))

    def delete_password(service: str, username: str) -> None:
        fake_keyring.pop((service, username), None)

    with (
        patch("navi.secrets.store.keyring.set_password", side_effect=set_password),
        patch("navi.secrets.store.keyring.get_password", side_effect=get_password),
        patch(
            "navi.secrets.store.keyring.delete_password",
            side_effect=delete_password,
        ),
    ):
        yield fake_keyring


def test_set_get_delete_provider_key(
    keyring_backend: dict[tuple[str, str], str],
) -> None:
    set_provider_key("groq", "secret-value")
    assert get_provider_key("groq") == "secret-value"

    delete_provider_key("groq")
    assert get_provider_key("groq") is None


def test_list_configured_providers(keyring_backend: dict[tuple[str, str], str]) -> None:
    set_provider_key("groq", "a")
    set_provider_key("deepgram", "b")

    configured = list_configured_providers()
    assert configured == ["groq", "deepgram"]


def test_unknown_provider_raises(keyring_backend: dict[tuple[str, str], str]) -> None:
    with pytest.raises(SecretsError, match="Unknown provider"):
        set_provider_key("unknown", "value")


def test_key_not_in_error_message(keyring_backend: dict[tuple[str, str], str]) -> None:
    set_provider_key("groq", "super-secret-key")
    with pytest.raises(SecretsError, match="Unknown provider"):
        set_provider_key("bad", "value")

    assert "super-secret-key" not in str(
        SecretsError(
            "Unknown provider 'bad'. Supported: groq, deepgram, assemblyai, gladia"
        )
    )
