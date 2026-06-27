"""STT provider abstraction and implementations."""

from navi.providers.base import STTProvider
from navi.providers.capabilities import (
    ProviderCapabilities,
    all_capabilities,
    provider_capabilities,
)
from navi.providers.deepgram import DeepgramProvider
from navi.providers.errors import (
    STTAuthError,
    STTError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)
from navi.providers.groq import GroqProvider
from navi.providers.manager import resolve_provider
from navi.providers.pcm import pcm_to_wav_bytes
from navi.providers.registry import get_provider, list_providers, register_provider
from navi.providers.types import TranscriptionResult

__all__ = [
    "DeepgramProvider",
    "GroqProvider",
    "ProviderCapabilities",
    "STTAuthError",
    "STTError",
    "STTProvider",
    "STTProviderError",
    "STTRateLimitError",
    "STTTimeoutError",
    "TranscriptionResult",
    "all_capabilities",
    "get_provider",
    "list_providers",
    "pcm_to_wav_bytes",
    "provider_capabilities",
    "register_provider",
    "resolve_provider",
]
