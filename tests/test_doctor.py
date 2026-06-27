"""Tests for `navi doctor`."""

from pathlib import Path
from unittest.mock import patch

from navi.cli.doctor import CheckStatus, run_checks


def test_run_checks_includes_python_version() -> None:
    results = run_checks()
    names = [result.name for result in results]
    assert "Python version" in names


def test_run_checks_reports_invalid_config(tmp_path: Path) -> None:
    bad_config = tmp_path / "config.toml"
    bad_config.write_text("provider = [\n", encoding="utf-8")

    with patch("navi.cli.doctor.ConfigManager") as mock_manager:
        from navi.config import ConfigManager

        mock_manager.return_value = ConfigManager(bad_config)
        results = run_checks()

    config_result = next(result for result in results if result.name == "Configuration")
    assert config_result.status == CheckStatus.FAIL


def test_run_checks_warns_when_preferred_key_missing(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    manager_path = config_path

    with (
        patch("navi.cli.doctor.ConfigManager") as mock_manager,
        patch("navi.cli.doctor.get_provider_key", return_value=None),
    ):
        from navi.config import ConfigManager

        mock_manager.return_value = ConfigManager(manager_path)
        mock_manager.return_value.init()
        results = run_checks()

    key_result = next(
        result for result in results if result.name == "Preferred provider key"
    )
    assert key_result.status == CheckStatus.WARN
