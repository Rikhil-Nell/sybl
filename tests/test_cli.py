"""CLI smoke tests."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from sybl.cli import app

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "sybl" in result.stdout


def test_start_help() -> None:
    result = runner.invoke(app, ["start", "--help"])
    assert result.exit_code == 0
    assert "daemon" in result.stdout.lower()


def test_config_init_and_show(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"

    with patch("sybl.cli.config_cmd.ConfigManager") as mock_manager:
        from sybl.config import ConfigManager

        mock_manager.return_value = ConfigManager(config_file)

        init_result = runner.invoke(app, ["config", "init"])
        assert init_result.exit_code == 0
        assert config_file.exists()

        show_result = runner.invoke(app, ["config", "show"])
        assert show_result.exit_code == 0
        assert "groq" in show_result.stdout


def test_config_edit_writes_and_opens() -> None:
    opened: dict[str, Path] = {}

    def fake_open(path: Path) -> None:
        opened["path"] = path

    with (
        patch("sybl.cli.config_cmd.open_in_editor", side_effect=fake_open),
        patch("sybl.cli.config_cmd.is_daemon_running", return_value=False),
    ):
        result = runner.invoke(app, ["config", "edit"])

    assert result.exit_code == 0
    assert opened["path"].exists()
    assert "Saved" in result.stdout


def test_resolve_editor_command_honors_editor(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from sybl.config.edit import resolve_editor_command

    monkeypatch.setenv("EDITOR", "myedit --wait")
    monkeypatch.delenv("VISUAL", raising=False)
    command = resolve_editor_command(tmp_path / "config.toml")
    assert command[:2] == ["myedit", "--wait"]
    assert command[-1].endswith("config.toml")


def test_doctor_runs() -> None:
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code in (0, 1)
    assert "Python version" in result.stdout


def test_status_when_daemon_down() -> None:
    with patch("sybl.cli.status.is_daemon_running", return_value=False):
        result = runner.invoke(app, ["status"])
    assert result.exit_code == 1
    assert "not running" in (result.stdout + result.stderr).lower()


def test_tui_requires_daemon() -> None:
    with patch("sybl.cli.tui.is_daemon_running", return_value=False):
        result = runner.invoke(app, ["tui"])
    assert result.exit_code == 1
    assert "not running" in (result.stdout + result.stderr).lower()


def test_transcribe_help() -> None:
    result = runner.invoke(
        app,
        ["transcribe", "--help"],
        env={"NO_COLOR": "1", "TERM": "dumb"},
    )
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
