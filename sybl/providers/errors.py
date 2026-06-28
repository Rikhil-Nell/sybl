"""STT provider exception hierarchy."""


class STTError(Exception):
    """Base class for speech-to-text failures."""


class STTAuthError(STTError):
    """Missing or invalid provider API key."""


class STTRateLimitError(STTError):
    """Provider rate limit exceeded."""


class STTTimeoutError(STTError):
    """Network or provider timeout."""


class STTProviderError(STTError):
    """Other provider-side failures."""
