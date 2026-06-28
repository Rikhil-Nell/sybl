"""Tests for hotkey binding parsing."""

import pytest

from sybl.hotkeys.bindings import BindingParseError, parse_binding


def test_parse_default_binding() -> None:
    binding = parse_binding("ctrl+shift+space")
    assert binding.token_set == frozenset({"ctrl", "shift", "space"})


def test_parse_modifier_aliases() -> None:
    binding = parse_binding("control+win+space")
    assert binding.token_set == frozenset({"ctrl", "cmd", "space"})


def test_parse_single_character() -> None:
    binding = parse_binding("ctrl+shift+a")
    assert binding.token_set == frozenset({"ctrl", "shift", "a"})


def test_parse_esc_cancel_binding() -> None:
    binding = parse_binding("escape")
    assert binding.token_set == frozenset({"esc"})


def test_rejects_empty_binding() -> None:
    with pytest.raises(BindingParseError, match="empty"):
        parse_binding("   ")


def test_rejects_unknown_token() -> None:
    with pytest.raises(BindingParseError, match="Unknown"):
        parse_binding("ctrl+notakey")


def test_rejects_duplicate_tokens() -> None:
    with pytest.raises(BindingParseError, match="Duplicate"):
        parse_binding("ctrl+ctrl+space")
