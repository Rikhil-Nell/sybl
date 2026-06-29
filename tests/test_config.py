"""Tests for configuration loading and persistence."""

from pathlib import Path

import pytest

from sybl.config import ConfigError, ConfigManager, SyblConfig


def test_defaults_validate() -> None:
    config = SyblConfig()
    assert config.provider.preferred == "groq"
    assert config.provider.groq.model == "whisper-large-v3-turbo"
    assert config.audio.sample_rate == 16000
    assert config.audio.block_duration_ms == 20
    assert config.audio.save_last_recording is True
    assert config.logging.ring_buffer_size == 500
    assert config.hotkey.mode == "both"
    assert config.hotkey.cancel_binding == "esc"
    assert config.hotkey.streaming == "auto"
    assert config.hotkey.min_duration_ms == 250
    assert config.inject.enabled is True
    assert config.inject.strategy == "paste"
    assert config.inject.restore_clipboard is True
    assert config.postprocess.enabled is True
    assert config.postprocess.trim_fillers is True
    assert config.postprocess.capitalize is True
    assert config.postprocess.ensure_punctuation is False
    assert config.postprocess.collapse_repeated_words is False
    assert config.postprocess.normalize_quotes is True
    assert config.ipc.host == "127.0.0.1"
    assert config.ipc.history_size == 100
    assert config.vocabulary.enabled is True
    assert config.voice_commands.enabled is True
    assert config.indicator.enabled is True
    assert config.indicator.strategy == "overlay"
    assert config.indicator.size_px == 48
    assert config.ui.onboarding_complete is False


def test_load_returns_defaults_when_missing(tmp_config_path: Path) -> None:
    manager = ConfigManager(tmp_config_path)
    config = manager.load()
    assert config.hotkey.binding == "ctrl+alt+space"
    assert not tmp_config_path.exists()


def test_init_creates_config_file(tmp_config_path: Path) -> None:
    manager = ConfigManager(tmp_config_path)
    config = manager.init()
    assert tmp_config_path.exists()
    assert config.provider.fallback_order == ["deepgram", "groq"]


def test_round_trip_save_load(tmp_config_path: Path) -> None:
    manager = ConfigManager(tmp_config_path)
    original = SyblConfig()
    original.provider.preferred = "deepgram"
    original.audio.device = "Microphone (USB)"
    manager.save(original)

    loaded = manager.load()
    assert loaded.provider.preferred == "deepgram"
    assert loaded.audio.device == "Microphone (USB)"


def test_invalid_toml_raises_config_error(tmp_config_path: Path) -> None:
    tmp_config_path.write_text("provider = [", encoding="utf-8")
    manager = ConfigManager(tmp_config_path)

    with pytest.raises(ConfigError, match="Invalid TOML"):
        manager.load()


def test_invalid_schema_raises_config_error(tmp_config_path: Path) -> None:
    tmp_config_path.write_text(
        '[audio]\nsample_rate = "not-a-number"\n',
        encoding="utf-8",
    )
    manager = ConfigManager(tmp_config_path)

    with pytest.raises(ConfigError, match="Invalid configuration"):
        manager.load()


def test_invalid_hotkey_binding_raises() -> None:
    with pytest.raises(ValueError, match="Invalid hotkey binding"):
        SyblConfig(hotkey={"binding": "not+a+valid+binding!!!"})


def test_migrates_legacy_hotkey_binding(tmp_config_path: Path) -> None:
    tmp_config_path.write_text(
        '[hotkey]\nbinding = "ctrl+shift+space"\n',
        encoding="utf-8",
    )
    manager = ConfigManager(tmp_config_path)
    config = manager.load()

    assert config.hotkey.binding == "ctrl+alt+space"
    reloaded = manager.load()
    assert reloaded.hotkey.binding == "ctrl+alt+space"
