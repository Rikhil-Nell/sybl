"""Tests for CLI overhaul (help panels, config get/set, --json, banner, wizards)."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from sybl.cli import app
from sybl.cli import exit_codes as ec
from sybl.config import ConfigManager, SyblConfig

runner = CliRunner()


def test_help_shows_categorized_panels() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    output = result.stdout
    for panel in ("Daemon", "Dictation", "Configuration", "Diagnostics"):
        assert panel in output
    assert "start" in output
    assert "providers" in output
    assert "setup" in output
    assert "logs" in output
    assert "restart" in output


def test_bare_sybl_shows_banner_and_help() -> None:
    result = runner.invoke(app, [])
    assert result.exit_code == 0
    assert "sybl" in result.stdout.lower() or "✦" in result.stdout
    assert "Commands" in result.stdout or "start" in result.stdout


def test_config_get_set_round_trip() -> None:
    manager = ConfigManager()
    manager.init()

    set_result = runner.invoke(
        app,
        ["config", "set", "provider.preferred", "deepgram"],
    )
    assert set_result.exit_code == 0, set_result.stdout

    get_result = runner.invoke(app, ["config", "get", "provider.preferred"])
    assert get_result.exit_code == 0
    assert get_result.stdout.strip() == "deepgram"

    loaded = manager.load()
    assert loaded.provider.preferred == "deepgram"


def test_config_show_json() -> None:
    manager = ConfigManager()
    manager.init()

    result = runner.invoke(app, ["config", "show", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["provider"]["preferred"] == "groq"


def test_doctor_json_shape() -> None:
    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code in (0, ec.GENERAL_ERROR)
    payload = json.loads(result.stdout)
    assert "checks" in payload
    assert "ok" in payload
    assert isinstance(payload["checks"], list)
    assert payload["checks"]
    first = payload["checks"][0]
    assert {"name", "status", "detail"}.issubset(first.keys())


def test_providers_json_shape() -> None:
    result = runner.invoke(app, ["providers", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert "providers" in payload
    names = {item["name"] for item in payload["providers"]}
    assert "groq" in names
    assert "deepgram" in names
    sample = payload["providers"][0]
    assert {"streaming", "partial_results", "key_configured"}.issubset(sample.keys())


def test_status_json_when_daemon_down() -> None:
    with patch("sybl.cli.status.is_daemon_running", return_value=False):
        result = runner.invoke(app, ["status", "--json"])
    assert result.exit_code == ec.DAEMON_NOT_RUNNING


def test_banner_first_run_marks_shown() -> None:
    manager = ConfigManager()
    manager.init()

    with patch("sybl.cli.render_banner") as mock_banner:
        result = runner.invoke(app, ["config", "path"])

    assert result.exit_code == 0
    mock_banner.assert_called_once()
    config = manager.load()
    assert config.ui.first_run_shown is True


def test_banner_not_shown_after_first_run() -> None:
    manager = ConfigManager()
    config = SyblConfig(ui={"first_run_shown": True})
    manager.save(config)

    with patch("sybl.cli.render_banner") as mock_banner:
        result = runner.invoke(app, ["config", "path"])

    assert result.exit_code == 0
    mock_banner.assert_not_called()


def test_setup_bypass_with_no_input() -> None:
    result = runner.invoke(app, ["--no-input", "setup"])
    assert result.exit_code == ec.USAGE_ERROR
    assert "Interactive setup requires a TTY" in result.stdout + result.stderr


def test_set_key_bypass_with_no_input() -> None:
    result = runner.invoke(app, ["--no-input", "config", "set-key"])
    assert result.exit_code == ec.USAGE_ERROR
    assert "Provider required" in result.stdout + result.stderr


def test_set_key_bypass_with_no_input_and_provider() -> None:
    result = runner.invoke(app, ["--no-input", "config", "set-key", "groq"])
    assert result.exit_code == ec.USAGE_ERROR
    assert "--no-input" in result.stdout + result.stderr


def test_logs_tail(monkeypatch: pytest.MonkeyPatch) -> None:
    from sybl.config import log_path

    log_file = log_path()
    log_file.write_text("line1\nline2\nline3\n", encoding="utf-8")

    result = runner.invoke(app, ["logs", "-n", "2"])
    assert result.exit_code == 0
    lines = result.stdout.strip().splitlines()
    assert lines == ["line2", "line3"]
