"""Audio capture exceptions."""


class AudioError(Exception):
    """Base exception for audio capture errors."""


class DeviceNotFoundError(AudioError):
    """Raised when the configured input device cannot be resolved."""


class StreamError(AudioError):
    """Raised when the audio stream fails or is interrupted."""


class SessionError(AudioError):
    """Raised when session lifecycle operations are invalid."""
