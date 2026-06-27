"""Session-start STT provider selection."""

from __future__ import annotations

import logging

from navi.config.models import NaviConfig
from navi.providers.base import STTProvider
from navi.providers.capabilities import provider_capabilities
from navi.providers.errors import STTProviderError
from navi.providers.registry import get_provider, list_providers
from navi.secrets.store import get_provider_key

logger = logging.getLogger("navi.providers.manager")


def _build_candidates(
    config: NaviConfig,
    *,
    prefer: str | None,
    streaming_required: bool,
) -> list[str]:
    candidates: list[str] = []
    if prefer:
        candidates.append(prefer.strip().lower())
    preferred = config.provider.preferred.strip().lower()
    if preferred not in candidates:
        candidates.append(preferred)
    for name in config.provider.fallback_order:
        normalized = name.strip().lower()
        if normalized not in candidates:
            candidates.append(normalized)

    if streaming_required:
        for name in list_providers():
            try:
                caps = provider_capabilities(name)
            except KeyError:
                continue
            if caps.streaming and name not in candidates:
                candidates.append(name)

    return candidates


def resolve_provider(
    config: NaviConfig,
    *,
    prefer: str | None = None,
    streaming_required: bool = False,
) -> tuple[str, STTProvider]:
    """Pick a provider at session start using preferred + fallback order."""
    candidates = _build_candidates(
        config,
        prefer=prefer,
        streaming_required=streaming_required,
    )

    skipped: list[str] = []
    for name in candidates:
        try:
            caps = provider_capabilities(name)
        except KeyError:
            skipped.append(f"{name} (unknown)")
            continue

        if streaming_required and not caps.streaming:
            skipped.append(f"{name} (no streaming)")
            continue

        if caps.requires_key and not get_provider_key(name):
            skipped.append(f"{name} (no key)")
            continue

        provider = get_provider(name, config)
        if skipped:
            logger.info(
                "Selected provider %s; skipped: %s",
                name,
                ", ".join(skipped),
            )
        return name, provider

    detail = ", ".join(skipped) if skipped else "none registered"
    raise STTProviderError(
        "No available STT provider for this session. "
        f"Checked: {', '.join(candidates)}. Skipped: {detail}."
    )
