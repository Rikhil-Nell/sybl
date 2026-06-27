"""Pydantic configuration models."""

from typing import Literal

from pydantic import BaseModel, Field


class GroqConfig(BaseModel):
    model: str = "whisper-large-v3-turbo"
    language: str | None = None
    prompt: str | None = None
    temperature: float = 0.0


class DeepgramConfig(BaseModel):
    model: str = "nova-3"
    language: str | None = None
    punctuate: bool = True
    smart_format: bool = True
    interim_results: bool = True


class ProviderConfig(BaseModel):
    preferred: str = "groq"
    fallback_order: list[str] = Field(default_factory=lambda: ["deepgram", "groq"])
    groq: GroqConfig = Field(default_factory=GroqConfig)
    deepgram: DeepgramConfig = Field(default_factory=DeepgramConfig)


class HotkeyConfig(BaseModel):
    # ctrl+shift+space conflicts with Windows Terminal (new window); alt avoids that.
    binding: str = "ctrl+alt+space"
    mode: Literal["ptt"] = "ptt"
    cancel_binding: str = "esc"
    streaming: Literal["auto", "on", "off"] = "auto"
    min_duration_ms: int = 250


class InjectConfig(BaseModel):
    enabled: bool = True
    strategy: Literal["paste"] = "paste"
    restore_clipboard: bool = True


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
    inject: InjectConfig = Field(default_factory=InjectConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
