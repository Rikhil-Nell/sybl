"""Tests for capture indicator wiring in NaviDaemon."""

from contextlib import ExitStack
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from navi.core.state import SessionState


def _enter_daemon_patches(stack: ExitStack, mock_indicator: MagicMock) -> None:
    mock_hotkeys = MagicMock()
    mock_hotkeys.stop = AsyncMock()
    mock_controller = MagicMock()
    mock_controller.shutdown = AsyncMock()
    stack.enter_context(
        patch("navi.core.daemon.create_indicator", return_value=mock_indicator)
    )
    stack.enter_context(patch("navi.core.daemon.setup_logging"))
    stack.enter_context(
        patch("navi.core.daemon.create_hotkey_manager", return_value=mock_hotkeys)
    )
    stack.enter_context(
        patch("navi.core.daemon.DictationController", return_value=mock_controller)
    )


@pytest.mark.asyncio
async def test_state_changed_shows_and_hides_indicator() -> None:
    mock_indicator = MagicMock()
    with ExitStack() as stack:
        _enter_daemon_patches(stack, mock_indicator)
        from navi.core.daemon import NaviDaemon

        daemon = NaviDaemon()
        await daemon._on_state_changed(SessionState.LISTENING)
        mock_indicator.show.assert_called_once()
        mock_indicator.hide.assert_not_called()

        await daemon._on_state_changed(SessionState.IDLE)
        mock_indicator.hide.assert_called_once()
        await daemon.shutdown()


@pytest.mark.asyncio
async def test_poll_levels_updates_indicator() -> None:
    mock_indicator = MagicMock()
    mock_controller = MagicMock()
    mock_controller.shutdown = AsyncMock()
    mock_controller.current_level = 0.42
    mock_controller.state = SessionState.LISTENING

    async def stop_after_one_sleep(_seconds: float) -> None:
        mock_controller.state = SessionState.IDLE

    with ExitStack() as stack:
        _enter_daemon_patches(stack, mock_indicator)
        stack.enter_context(patch("asyncio.sleep", side_effect=stop_after_one_sleep))
        from navi.core.daemon import NaviDaemon

        daemon = NaviDaemon()
        daemon._controller = mock_controller
        await daemon._poll_levels()
        mock_indicator.update_level.assert_called_once_with(0.42)
        await daemon.shutdown()
