"""Tests for provider capabilities and session-start selection."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sybl.config.models import SyblConfig
from sybl.providers.capabilities import provider_capabilities
from sybl.providers.errors import STTProviderError
from sybl.providers.manager import resolve_provider


def test_groq_capabilities() -> None:
    caps = provider_capabilities("groq")
    assert caps.streaming is False
    assert caps.partial_results is False


def test_deepgram_capabilities() -> None:
    caps = provider_capabilities("deepgram")
    assert caps.streaming is True
    assert caps.partial_results is True


def test_resolve_provider_prefers_configured() -> None:
    config = SyblConfig()
    with patch("sybl.providers.manager.get_provider_key", return_value="key"):
        provider_id, _provider = resolve_provider(config, prefer="groq")
    assert provider_id == "groq"


def test_resolve_provider_falls_back_when_preferred_missing_key() -> None:
    config = SyblConfig()
    config.provider.preferred = "deepgram"

    def fake_key(name: str) -> str | None:
        return "groq-key" if name == "groq" else None

    with patch("sybl.providers.manager.get_provider_key", side_effect=fake_key):
        provider_id, _provider = resolve_provider(config)
    assert provider_id == "groq"


def test_resolve_provider_requires_streaming_capability() -> None:
    config = SyblConfig()

    def fake_key(name: str) -> str | None:
        return "key"

    with patch("sybl.providers.manager.get_provider_key", side_effect=fake_key):
        provider_id, _provider = resolve_provider(
            config,
            prefer="groq",
            streaming_required=True,
        )
    assert provider_id == "deepgram"


def test_resolve_provider_raises_when_none_available() -> None:
    config = SyblConfig()
    with patch("sybl.providers.manager.get_provider_key", return_value=None):
        with pytest.raises(STTProviderError, match="No available STT provider"):
            resolve_provider(config, streaming_required=True)


def test_resolve_streaming_includes_registered_streaming_providers() -> None:
    """Legacy configs with fallback_order=['groq'] should still find deepgram."""
    config = SyblConfig()
    config.provider.fallback_order = ["groq"]

    with patch("sybl.providers.manager.get_provider_key", return_value="key"):
        provider_id, _provider = resolve_provider(config, streaming_required=True)

    assert provider_id == "deepgram"
