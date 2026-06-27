"""CLI smoke tests."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from navi.cli import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Navi" in result.stdout


def test_start_help() -> None:
    result = runner.invoke(app, ["start", "--help"])
    assert result.exit_code == 0
    assert "daemon" in result.stdout.lower()


def test_config_init_and_show(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"

    with patch("navi.cli.config_cmd.ConfigManager") as mock_manager:
        from navi.config import ConfigManager

        mock_manager.return_value = ConfigManager(config_file)

        init_result = runner.invoke(app, ["config", "init"])
        assert init_result.exit_code == 0
        assert config_file.exists()

        show_result = runner.invoke(app, ["config", "show"])
        assert show_result.exit_code == 0
        assert "groq" in show_result.stdout


def test_doctor_runs() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code in (0, 1)
    assert "Python version" in result.stdout


def test_tui_stub() -> None:
    result = runner.invoke(app, ["tui"])
    assert result.exit_code == 0
    assert "Phase 7" in result.stdout


def test_transcribe_help() -> None:
    result = runner.invoke(app, ["transcribe", "--help"])
    assert result.exit_code == 0
    assert "transcribe" in result.stdout.lower()
    assert "--seconds" in result.stdout
    assert "--stream" in result.stdout


def test_hotkey_help() -> None:
    result = runner.invoke(app, ["hotkey", "--help"])
    assert result.exit_code == 0
    assert "test" in result.stdout.lower()


def test_hotkey_test_help() -> None:
    result = runner.invoke(app, ["hotkey", "test", "--help"])
    assert result.exit_code == 0
    assert "activate" in result.stdout.lower()
