"""Tests for CLI I/O helpers."""

from __future__ import annotations

from unittest.mock import patch

from navi.cli.io import echo_error


def test_echo_error_falls_back_to_stdout_on_oserror(capsys) -> None:
    with patch("navi.cli.io.typer.echo", side_effect=[OSError(6), None]) as mock_echo:
        echo_error("Navi daemon is not running.")

    assert mock_echo.call_count == 2
    mock_echo.assert_any_call("Navi daemon is not running.", err=True)
    mock_echo.assert_any_call("Navi daemon is not running.")
