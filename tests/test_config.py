"""Tests for configuration loading and persistence."""

from pathlib import Path

import pytest

from navi.config import ConfigError, ConfigManager, NaviConfig


def test_defaults_validate() -> None:
    config = NaviConfig()
    assert config.provider.preferred == "groq"
    assert config.provider.groq.model == "whisper-large-v3-turbo"
    assert config.audio.sample_rate == 16000
    assert config.audio.block_duration_ms == 20
    assert config.audio.save_last_recording is True
    assert config.logging.ring_buffer_size == 500


def test_load_returns_defaults_when_missing(tmp_config_path: Path) -> None:
    manager = ConfigManager(tmp_config_path)
    config = manager.load()
    assert config.hotkey.binding == "ctrl+shift+space"
    assert not tmp_config_path.exists()


def test_init_creates_config_file(tmp_config_path: Path) -> None:
    manager = ConfigManager(tmp_config_path)
    config = manager.init()
    assert tmp_config_path.exists()
    assert config.provider.fallback_order == ["groq"]


def test_round_trip_save_load(tmp_config_path: Path) -> None:
    manager = ConfigManager(tmp_config_path)
    original = NaviConfig()
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
