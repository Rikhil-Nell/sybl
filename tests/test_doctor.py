"""Tests for `sybl doctor`."""

from pathlib import Path
from unittest.mock import patch

from sybl.cli.doctor import CheckStatus, run_checks


def test_run_checks_includes_python_version() -> None:
    results = run_checks()
    names = [result.name for result in results]
    assert "Python version" in names


def test_run_checks_reports_invalid_config(tmp_path: Path) -> None:
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("provider = [\n", encoding="utf-8")

    with patch("sybl.cli.doctor.ConfigManager") as mock_manager:
        from sybl.config import ConfigManager

        mock_manager.return_value = ConfigManager(bad_config)
        results = run_checks()

    config_result = next(result for result in results if result.name == "Configuration")
    assert config_result.status == CheckStatus.FAIL


def test_run_checks_warns_when_preferred_key_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    manager_path = config_path

    with (
        patch("sybl.cli.doctor.ConfigManager") as mock_manager,
        patch("sybl.cli.doctor.get_provider_key", return_value=None),
    ):
        from sybl.config import ConfigManager

        mock_manager.return_value = ConfigManager(manager_path)
        mock_manager.return_value.init()
        results = run_checks()

    key_result = next(
        result for result in results if result.name == "Preferred provider key"
    )
    assert key_result.status == CheckStatus.WARN


def test_run_checks_live_includes_live_section() -> None:
    from sybl.cli.doctor import CheckResult

    live_result = CheckResult(
        "Daemon IPC ping (live)",
        CheckStatus.PASS,
        "pong",
    )
    with patch(
        "sybl.cli.doctor._run_live_checks",
        return_value=[live_result],
    ):
        results = run_checks(live=True)
    assert any(result.name == "Daemon IPC ping (live)" for result in results)


def test_static_checks_exclude_live_probes_by_default() -> None:
    results = run_checks(live=False)
    assert not any("live" in result.name.lower() for result in results)
