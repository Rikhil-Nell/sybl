"""Tests for final-transcript voice command parsing."""

from navi.config.models import VoiceCommandsConfig
from navi.core.voice_commands import apply_voice_commands


def test_new_line_inserts_line_break() -> None:
    config = VoiceCommandsConfig()
    result = apply_voice_commands(config, "hello new line world")
    assert result.text == "hello\nworld"
    assert result.skip_inject is False


def test_scratch_that_skips_inject() -> None:
    config = VoiceCommandsConfig()
    result = apply_voice_commands(config, "scratch that")
    assert result.text == ""
    assert result.skip_inject is True


def test_period_and_comma_insert_punctuation() -> None:
    config = VoiceCommandsConfig()
    result = apply_voice_commands(config, "hello period new line world comma")
    assert result.text == "hello .\nworld ,"
    assert result.skip_inject is False


def test_disabled_passthrough() -> None:
    config = VoiceCommandsConfig(enabled=False)
    result = apply_voice_commands(config, "scratch that")
    assert result.text == "scratch that"
    assert result.skip_inject is False
