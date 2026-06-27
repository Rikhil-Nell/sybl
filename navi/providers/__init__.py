"""STT provider abstraction and implementations."""

from navi.providers.base import STTProvider
from navi.providers.errors import (
    STTAuthError,
    STTError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)
from navi.providers.groq import GroqProvider
from navi.providers.pcm import pcm_to_wav_bytes
from navi.providers.registry import get_provider, list_providers, register_provider
from navi.providers.types import TranscriptionResult

__all__ = [
    "GroqProvider",
    "STTAuthError",
    "STTError",
    "STTProvider",
    "STTProviderError",
    "STTRateLimitError",
    "STTTimeoutError",
    "TranscriptionResult",
    "get_provider",
    "list_providers",
    "pcm_to_wav_bytes",
    "register_provider",
]
