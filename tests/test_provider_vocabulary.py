"""Tests for vocabulary propagation to STT providers."""

from sybl.config.models import DeepgramConfig, GroqConfig
from sybl.providers.deepgram import DeepgramProvider
from sybl.providers.groq import GroqProvider


def test_groq_builds_prompt_from_vocabulary_when_unset() -> None:
    provider = GroqProvider(GroqConfig(), vocabulary=["Rikhil", "sybl"])
    assert provider._effective_prompt() == "Common terms: Rikhil, sybl"


def test_groq_manual_prompt_overrides_vocabulary() -> None:
    provider = GroqProvider(
        GroqConfig(prompt="Custom prompt"),
        vocabulary=["Rikhil"],
    )
    assert provider._effective_prompt() == "Custom prompt"


def test_deepgram_connect_kwargs_include_keyterms() -> None:
    provider = DeepgramProvider(
        DeepgramConfig(),
        vocabulary=["Rikhil", "sybl"],
    )
    kwargs = provider._connect_kwargs()
    assert kwargs["keyterm"] == ["Rikhil", "sybl"]
