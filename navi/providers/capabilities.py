"""Provider capability metadata."""

from __future__ import annotations

from dataclasses import dataclass

_CAPABILITIES: dict[str, ProviderCapabilities] = {}


@dataclass(frozen=True)
class ProviderCapabilities:
    name: str
    streaming: bool
    partial_results: bool
    requires_key: bool


def _register(cap: ProviderCapabilities) -> ProviderCapabilities:
    _CAPABILITIES[cap.name] = cap
    return cap


GROQ_CAPABILITIES = _register(
    ProviderCapabilities(
        name="groq",
        streaming=False,
        partial_results=False,
        requires_key=True,
    )
)

DEEPGRAM_CAPABILITIES = _register(
    ProviderCapabilities(
        name="deepgram",
        streaming=True,
        partial_results=True,
        requires_key=True,
    )
)


def provider_capabilities(name: str) -> ProviderCapabilities:
    normalized = name.strip().lower()
    caps = _CAPABILITIES.get(normalized)
    if caps is None:
        raise KeyError(f"Unknown provider capabilities for {name!r}")
    return caps


def all_capabilities() -> list[ProviderCapabilities]:
    return sorted(_CAPABILITIES.values(), key=lambda cap: cap.name)
