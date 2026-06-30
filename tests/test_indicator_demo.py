"""Tests for demo-mode indicator wiring and indicator demo CLI."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sybl.config.models import IndicatorConfig, SyblConfig
from sybl.tui.demo_indicator import DemoIndicatorBridge


class _StubIndicator:
    degraded = False

    def __init__(self) -> None:
        self.show_calls = 0
        self.hide_calls = 0
        self.phase_calls: list[str] = []
        self.shutdown_calls = 0

    def show(self) -> None:
        self.show_calls += 1

    def hide(self) -> None:
        self.hide_calls += 1

    def update_level(self, level: float) -> None:
        return None

    def set_phase(self, phase: str) -> None:
        self.phase_calls.append(phase)

    def shutdown(self) -> None:
        self.shutdown_calls += 1


@patch("sybl.tui.demo_indicator.create_indicator")
def test_demo_indicator_bridge_show_on_listening(mock_create: MagicMock) -> None:
    indicator = _StubIndicator()
    mock_create.return_value = indicator
    config = SyblConfig(indicator=IndicatorConfig(strategy="pill"))

    bridge = DemoIndicatorBridge(config)
    assert bridge.active

    bridge.on_state("listening")
    assert indicator.show_calls == 1

    bridge.on_state("idle")
    assert indicator.hide_calls == 1

    bridge.shutdown()
    assert indicator.shutdown_calls == 1


@patch("sybl.tui.demo_indicator.create_indicator")
def test_demo_indicator_bridge_processing_phase(mock_create: MagicMock) -> None:
    indicator = _StubIndicator()
    mock_create.return_value = indicator
    config = SyblConfig(indicator=IndicatorConfig(strategy="pill"))

    bridge = DemoIndicatorBridge(config)
    bridge.on_state("listening")
    bridge.on_state("processing")
    assert indicator.phase_calls == ["processing"]
    assert indicator.hide_calls == 0
    bridge.shutdown()


@patch("sybl.tui.demo_indicator.create_indicator")
def test_demo_indicator_bridge_skips_when_disabled(mock_create: MagicMock) -> None:
    config = SyblConfig(indicator=IndicatorConfig(enabled=False))
    bridge = DemoIndicatorBridge(config)
    assert not bridge.active
    mock_create.assert_not_called()


@patch("sybl.cli.indicator_cmd.create_indicator")
@patch("sybl.cli.indicator_cmd.ConfigManager")
def test_indicator_demo_command(
    mock_cfg: MagicMock,
    mock_create: MagicMock,
) -> None:
    from sybl.cli import app

    indicator = _StubIndicator()
    mock_create.return_value = indicator
    mock_cfg.return_value.load.return_value = SyblConfig(
        indicator=IndicatorConfig(strategy="pill", enabled=True),
    )

    runner = CliRunner()
    result = runner.invoke(app, ["indicator", "demo", "--pill", "-d", "0.05"])
    assert result.exit_code == 0, result.output
    assert "StubIndicator" in result.output or "Indicator:" in result.output
    assert indicator.show_calls >= 1
