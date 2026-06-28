"""Tests for post-processing pipeline."""

from navi.config.models import PostProcessConfig
from navi.core.postprocess import (
    capitalize_first,
    ensure_terminal_punctuation,
    normalize_whitespace,
    process_text,
    trim_filler_words,
)


def test_normalize_whitespace_collapses_runs() -> None:
    assert normalize_whitespace("  hello   world  ") == "hello world"


def test_trim_filler_words_removes_leading_and_trailing() -> None:
    assert trim_filler_words("um uh hello world erm") == "hello world"
    assert trim_filler_words("UM, hello") == "hello"


def test_capitalize_first() -> None:
    assert capitalize_first("hello world") == "Hello world"
    assert capitalize_first("123 test") == "123 Test"


def test_ensure_terminal_punctuation_adds_period() -> None:
    assert ensure_terminal_punctuation("hello world") == "hello world."
    assert ensure_terminal_punctuation("hello world.") == "hello world."
    assert ensure_terminal_punctuation("Really?") == "Really?"


def test_process_text_disabled_passthrough() -> None:
    config = PostProcessConfig(enabled=False)
    raw = "um hello"
    assert process_text(config, raw) == raw


def test_process_text_default_pipeline() -> None:
    config = PostProcessConfig()
    assert process_text(config, "  um uh hello world erm  ") == "Hello world"


def test_process_text_with_punctuation_enabled() -> None:
    config = PostProcessConfig(ensure_punctuation=True)
    assert process_text(config, "um hello world") == "Hello world."


def test_normalize_quotes() -> None:
    from navi.core.postprocess import normalize_quotes

    assert normalize_quotes("“hello”") == '"hello"'


def test_trim_space_before_punctuation() -> None:
    from navi.core.postprocess import trim_space_before_punctuation

    assert trim_space_before_punctuation("hello .") == "hello."


def test_collapse_repeated_words() -> None:
    from navi.core.postprocess import collapse_repeated_words

    assert collapse_repeated_words("the the cat") == "the cat"


def test_process_text_empty_passthrough() -> None:
    config = PostProcessConfig()
    assert process_text(config, "   ") == "   "
