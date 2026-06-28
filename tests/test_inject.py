"""Tests for text injection."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from sybl.config.models import InjectConfig, SyblConfig
from sybl.hotkeys.focus import FocusTarget
from sybl.inject.base import InjectError
from sybl.inject.clipboard_win import ClipboardPasteInjector


@pytest.fixture
def injector() -> ClipboardPasteInjector:
    return ClipboardPasteInjector(InjectConfig())


@pytest.mark.asyncio
async def test_inject_sets_pastes_and_restores_clipboard(
    injector: ClipboardPasteInjector,
) -> None:
    target = FocusTarget(hwnd=123, pid=456, title="Notepad")

    with (
        patch(
            "sybl.inject.clipboard_win.read_clipboard_safe",
            return_value="prior text",
        ) as mock_read,
        patch("sybl.inject.clipboard_win.set_clipboard") as mock_set,
        patch("sybl.inject.clipboard_win.restore_focus") as mock_focus,
        patch("sybl.inject.clipboard_win.simulate_paste") as mock_paste,
    ):
        await injector.inject("hello world", target)

    mock_read.assert_called_once()
    assert mock_set.call_args_list[0].args[0] == "hello world"
    mock_focus.assert_called_once_with(target)
    mock_paste.assert_called_once()
    assert mock_set.call_args_list[-1].args[0] == "prior text"


@pytest.mark.asyncio
async def test_inject_skips_restore_when_disabled() -> None:
    injector = ClipboardPasteInjector(InjectConfig(restore_clipboard=False))

    with (
        patch("sybl.inject.clipboard_win.read_clipboard_safe") as mock_read,
        patch("sybl.inject.clipboard_win.set_clipboard") as mock_set,
        patch("sybl.inject.clipboard_win.restore_focus"),
        patch("sybl.inject.clipboard_win.simulate_paste"),
    ):
        await injector.inject("hello", None)

    mock_read.assert_not_called()
    mock_set.assert_called_once_with("hello")


@pytest.mark.asyncio
async def test_inject_wraps_unexpected_errors(injector: ClipboardPasteInjector) -> None:
    with (
        patch("sybl.inject.clipboard_win.read_clipboard_safe", return_value=None),
        patch(
            "sybl.inject.clipboard_win.set_clipboard",
            side_effect=RuntimeError("boom"),
        ),
    ):
        with pytest.raises(InjectError, match="Clipboard paste injection failed"):
            await injector.inject("hello", None)


def test_create_injector_on_windows() -> None:
    config = SyblConfig()
    with patch("sybl.inject.base.sys.platform", "win32"):
        from sybl.inject.base import create_injector

        injector = create_injector(config)
        assert isinstance(injector, ClipboardPasteInjector)


def test_create_injector_rejects_non_windows() -> None:
    config = SyblConfig()
    with patch("sybl.inject.base.sys.platform", "linux"):
        from sybl.inject.base import create_injector

        with pytest.raises(NotImplementedError, match="Windows-only"):
            create_injector(config)


def test_read_clipboard_safe_returns_skip_sentinel_on_oserror() -> None:
    with patch(
        "sybl.inject.clipboard_win.read_clipboard",
        side_effect=OSError("access violation"),
    ):
        from sybl.inject.clipboard_win import _SKIP_RESTORE, read_clipboard_safe

        assert read_clipboard_safe() is _SKIP_RESTORE
