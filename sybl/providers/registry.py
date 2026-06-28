"""Provider registry and factory."""

from __future__ import annotations

from collections.abc import Callable, Sequence

from sybl.config.models import SyblConfig
from sybl.providers.base import STTProvider
from sybl.providers.deepgram import DeepgramProvider
from sybl.providers.errors import STTProviderError
from sybl.providers.groq import GroqProvider

ProviderFactory = Callable[[SyblConfig, Sequence[str]], STTProvider]

_FACTORIES: dict[str, ProviderFactory] = {
    "groq": lambda config, vocabulary: GroqProvider(
        config.provider.groq,
        vocabulary=list(vocabulary),
    ),
    "deepgram": lambda config, vocabulary: DeepgramProvider(
        config.provider.deepgram,
        vocabulary=list(vocabulary),
    ),
}


def register_provider(name: str, factory: ProviderFactory) -> None:
    normalized = name.strip().lower()
    _FACTORIES[normalized] = factory


def get_provider(
    name: str,
    config: SyblConfig,
    *,
    vocabulary: Sequence[str] = (),
) -> STTProvider:
    normalized = name.strip().lower()
    factory = _FACTORIES.get(normalized)
    if factory is None:
        supported = ", ".join(sorted(_FACTORIES))
        raise STTProviderError(
            f"Unknown STT provider {name!r}. Supported: {supported}"
        )
    return factory(config, vocabulary)


def list_providers() -> list[str]:
    return sorted(_FACTORIES)
