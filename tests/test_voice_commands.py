"""Tests for final-transcript voice command parsing."""

from navi.config.models import VoiceCommandsConfig
from navi.core.voice_commands import apply_voice_commands


def test_new_line_inserts_line_break() -> None:
    config = VoiceCommandsConfig()
    assert apply_voice_commands(config, "hello new line world") == "hello\nworld"


def test_scratch_that_is_not_a_command() -> None:
    config = VoiceCommandsConfig()
    text = "My name is Rikhil. Scratch that."
    assert apply_voice_commands(config, text) == text


def test_period_and_comma_insert_punctuation() -> None:
    config = VoiceCommandsConfig()
    assert (
        apply_voice_commands(config, "hello period new line world comma")
        == "hello.\nworld,"
    )


def test_collapses_duplicate_punctuation_from_stt() -> None:
    config = VoiceCommandsConfig()
    result = apply_voice_commands(config, "investors ,, and more")
    assert result == "investors, and more"


def test_disabled_passthrough() -> None:
    config = VoiceCommandsConfig(enabled=False)
    result = apply_voice_commands(config, "hello new line world")
    assert result == "hello new line world"
