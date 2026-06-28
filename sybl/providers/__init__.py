"""STT provider abstraction and implementations."""

from sybl.providers.base import STTProvider
from sybl.providers.capabilities import (
    ProviderCapabilities,
    all_capabilities,
    provider_capabilities,
)
from sybl.providers.deepgram import DeepgramProvider
from sybl.providers.errors import (
    STTAuthError,
    STTError,
    STTProviderError,
    STTRateLimitError,
    STTTimeoutError,
)
from sybl.providers.groq import GroqProvider
from sybl.providers.manager import resolve_provider
from sybl.providers.pcm import pcm_to_wav_bytes
from sybl.providers.registry import get_provider, list_providers, register_provider
from sybl.providers.types import TranscriptionResult

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
