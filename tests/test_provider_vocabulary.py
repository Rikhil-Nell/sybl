"""Tests for vocabulary propagation to STT providers."""

from navi.config.models import DeepgramConfig, GroqConfig
from navi.providers.deepgram import DeepgramProvider
from navi.providers.groq import GroqProvider


def test_groq_builds_prompt_from_vocabulary_when_unset() -> None:
    provider = GroqProvider(GroqConfig(), vocabulary=["Rikhil", "Navi"])
    assert provider._effective_prompt() == "Common terms: Rikhil, Navi"


def test_groq_manual_prompt_overrides_vocabulary() -> None:
    provider = GroqProvider(
        GroqConfig(prompt="Custom prompt"),
        vocabulary=["Rikhil"],
    )
    assert provider._effective_prompt() == "Custom prompt"


def test_deepgram_connect_kwargs_include_keyterms() -> None:
    provider = DeepgramProvider(
        DeepgramConfig(),
        vocabulary=["Rikhil", "Navi"],
    )
    kwargs = provider._connect_kwargs()
    assert kwargs["keyterm"] == ["Rikhil", "Navi"]
