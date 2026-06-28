"""Tests for capture indicator factory and no-op implementation."""

from unittest.mock import patch

import pytest

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


def test_factory_overlay_on_non_windows() -> None:
    config = SyblConfig()
    with patch("sybl.indicator.sys.platform", "linux"):
        assert isinstance(create_indicator(config), NoOpIndicator)


@pytest.mark.integration
@pytest.mark.skipif(
    __import__("sys").platform != "win32",
    reason="Windows tkinter path",
)
def test_factory_overlay_on_windows() -> None:
    from sybl.indicator.tk_win import TkCaptureIndicator

    config = SyblConfig()
    indicator = create_indicator(config)
    try:
        assert isinstance(indicator, TkCaptureIndicator)
    finally:
        indicator.shutdown()
