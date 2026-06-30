"""Pydantic configuration models."""

from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    # ptt = hold only; toggle = double-press only; both = Wispr-style (default)
    mode: Literal["ptt", "toggle", "both"] = "both"
    cancel_binding: str = "esc"
    streaming: Literal["auto", "on", "off"] = "auto"
    min_duration_ms: int = 250
    ptt_hold_ms: int = Field(
        default=200,
        ge=100,
        le=500,
        description="Hold threshold before PTT activates in both mode",
    )
    toggle_double_press_ms: int = Field(default=400, ge=200, le=1000)

    @field_validator("binding", "cancel_binding")
    @classmethod
    def validate_binding_string(cls, value: str) -> str:
        from sybl.hotkeys.bindings import BindingParseError, parse_binding

        try:
            parse_binding(value)
        except BindingParseError as exc:
            msg = f"Invalid hotkey binding {value!r}: {exc}"
            raise ValueError(msg) from exc
        return value


class InjectConfig(BaseModel):
    enabled: bool = True
    strategy: Literal["paste"] = "paste"
    restore_clipboard: bool = True


class PostProcessConfig(BaseModel):
    enabled: bool = True
    trim_fillers: bool = True
    capitalize: bool = True
    ensure_punctuation: bool = False
    collapse_repeated_words: bool = False
    normalize_quotes: bool = True
    trim_space_before_punctuation: bool = True
    collapse_duplicate_punctuation: bool = True


class VocabularyConfig(BaseModel):
    enabled: bool = True


class VoiceCommandsConfig(BaseModel):
    enabled: bool = True


class AudioConfig(BaseModel):
    device: str | None = None
    sample_rate: int = 16000
    channels: int = 1
    block_duration_ms: int = 20
    save_last_recording: bool = True


class LoggingConfig(BaseModel):
    level: str = "INFO"
    ring_buffer_size: int = 500


class IpcConfig(BaseModel):
    host: str = "127.0.0.1"
    command_port: int = 0
    event_port: int = 0
    history_size: int = 100


class UiConfig(BaseModel):
    onboarding_complete: bool = False
    first_run_shown: bool = False


IndicatorAnchor = Literal[
    "top_center",
    "top_right",
    "top_left",
    "bottom_right",
    "bottom_left",
    "cursor",
]


class IndicatorConfig(BaseModel):
    enabled: bool = True
    strategy: Literal["overlay", "none", "pill"] = "pill"
    size_px: int = 72
    offset_x: int = 16
    offset_y: int = 16
    anchor: IndicatorAnchor = "top_center"
    margin_px: int = Field(default=0, ge=0, le=256)
    orb_accent: str = "#7b2ff7"
    orb_accent_secondary: str = "#f97316"
    orb_idle_opacity: float = Field(default=0.55, ge=0.0, le=1.0)
    orb_fps: int = Field(default=30, ge=15, le=60)
    sound_enabled: bool = False
    sound_on_start: bool = True
    sound_on_stop: bool = True
    sound_volume: float = Field(default=0.75, ge=0.0, le=1.0)
    sound_start_file: str | None = None
    sound_stop_file: str | None = None
    sound_max_seconds: float = Field(
        default=0.5,
        gt=0.0,
        le=2.0,
        description="Max cue length; longer WAV files are trimmed automatically",
    )

    @field_validator("strategy", mode="before")
    @classmethod
    def normalize_strategy(cls, value: object) -> object:
        if value in {"orb", "overlay"}:
            return "pill"
        return value


class SyblConfig(BaseModel):
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    hotkey: HotkeyConfig = Field(default_factory=HotkeyConfig)
    inject: InjectConfig = Field(default_factory=InjectConfig)
    postprocess: PostProcessConfig = Field(default_factory=PostProcessConfig)
    vocabulary: VocabularyConfig = Field(default_factory=VocabularyConfig)
    voice_commands: VoiceCommandsConfig = Field(default_factory=VoiceCommandsConfig)
    audio: AudioConfig = Field(default_factory=AudioConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    ipc: IpcConfig = Field(default_factory=IpcConfig)
    ui: UiConfig = Field(default_factory=UiConfig)
    indicator: IndicatorConfig = Field(default_factory=IndicatorConfig)
