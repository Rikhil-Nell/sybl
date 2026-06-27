"""Pydantic configuration models."""

from pydantic import BaseModel, Field


class ProviderConfig(BaseModel):
    preferred: str = "groq"
    fallback_order: list[str] = Field(default_factory=lambda: ["groq"])


class HotkeyConfig(BaseModel):
    binding: str = "ctrl+shift+space"


class AudioConfig(BaseModel):
    device: str | None = None
    sample_rate: int = 16000
    channels: int = 1
    block_duration_ms: int = 20
    save_last_recording: bool = True


class LoggingConfig(BaseModel):
    level: str = "INFO"
    ring_buffer_size: int = 500


class NaviConfig(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
