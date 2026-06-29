"""Tests for TUI settings hotkey validation."""

from __future__ import annotations

import pytest

from sybl.hotkeys.bindings import BindingParseError, parse_binding


def test_settings_hotkey_bindings_validate() -> None:
    parse_binding("ctrl+alt+space")
    parse_binding("esc")


def test_settings_hotkey_bindings_reject_invalid() -> None:
    with pytest.raises(BindingParseError):
        parse_binding("!!!")
