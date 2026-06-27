"""Provider registry and factory."""

from __future__ import annotations

from collections.abc import Callable

from navi.config.models import NaviConfig
from navi.providers.base import STTProvider
from navi.providers.deepgram import DeepgramProvider
from navi.providers.errors import STTProviderError
from navi.providers.groq import GroqProvider

ProviderFactory = Callable[[NaviConfig], STTProvider]

_FACTORIES: dict[str, ProviderFactory] = {
    "groq": lambda config: GroqProvider(config.provider.groq),
    "deepgram": lambda config: DeepgramProvider(config.provider.deepgram),
}


def register_provider(name: str, factory: ProviderFactory) -> None:
    normalized = name.strip().lower()
    _FACTORIES[normalized] = factory


def get_provider(name: str, config: NaviConfig) -> STTProvider:
    normalized = name.strip().lower()
    factory = _FACTORIES.get(normalized)
    if factory is None:
        supported = ", ".join(sorted(_FACTORIES))
        raise STTProviderError(
            f"Unknown STT provider {name!r}. Supported: {supported}"
        )
    return factory(config)


def list_providers() -> list[str]:
    return sorted(_FACTORIES)
