"""Tests for capture indicator factory and no-op implementation."""

from unittest.mock import MagicMock, patch

from sybl.config.models import IndicatorConfig, SyblConfig
from sybl.indicator import create_indicator
from sybl.indicator.noop import NoOpIndicator


def test_noop_indicator_methods() -> None:
    indicator = NoOpIndicator()
    indicator.show()
    indicator.hide()
    indicator.update_level(0.5)
    indicator.shutdown()


def test_factory_disabled() -> None:
    config = SyblConfig(indicator=IndicatorConfig(enabled=False))
    assert isinstance(create_indicator(config), NoOpIndicator)


def test_factory_strategy_none() -> None:
    config = SyblConfig(indicator=IndicatorConfig(strategy="none"))
    assert isinstance(create_indicator(config), NoOpIndicator)


def test_factory_default_strategy_is_pill() -> None:
    assert IndicatorConfig().strategy == "pill"


def test_strategy_overlay_normalizes_to_pill() -> None:
    cfg = IndicatorConfig(strategy="overlay")  # type: ignore[arg-type]
    assert cfg.strategy == "pill"


def test_factory_pill_on_non_windows() -> None:
    config = SyblConfig()
    with patch("sybl.indicator.sys.platform", "linux"):
        assert isinstance(create_indicator(config), NoOpIndicator)


@patch("sybl.indicator.pill_qt_win.subprocess.Popen")
@patch("sybl.indicator.qt_available", return_value=True)
def test_factory_pill_on_windows(mock_qt: MagicMock, mock_popen: MagicMock) -> None:
    import sys

    if sys.platform != "win32":
        return

    from sybl.indicator.pill_qt_win import QtPillIndicator

    fake = MagicMock()
    fake.stdin = MagicMock()
    fake.stdout = MagicMock()
    fake.stdout.readline.return_value = "ready\n"
    fake.stderr = MagicMock()
    fake.pid = 1
    fake.poll.return_value = None
    mock_popen.return_value = fake

    config = SyblConfig()
    indicator = create_indicator(config)
    try:
        assert isinstance(indicator, QtPillIndicator)
    finally:
        indicator.shutdown()
