"""Tests for pill NDJSON protocol and QtPillIndicator wrapper."""

from __future__ import annotations

import json
from io import StringIO
from unittest.mock import MagicMock, patch

from sybl.config.models import IndicatorConfig, SyblConfig
from sybl.indicator import create_indicator
from sybl.indicator.pill_qt_win import QtPillIndicator
from sybl.indicator.protocol import (
    config_payload,
    parse_command,
    serialize_command,
)


def test_serialize_show_command() -> None:
    assert serialize_command({"show": True}) == '{"show":true}'


def test_serialize_hide_command() -> None:
    assert serialize_command({"hide": True}) == '{"hide":true}'


def test_serialize_level_command() -> None:
    assert serialize_command({"level": 0.75}) == '{"level":0.75}'


def test_serialize_phase_command() -> None:
    assert serialize_command({"phase": "processing"}) == '{"phase":"processing"}'


def test_serialize_quit_command() -> None:
    assert serialize_command({"quit": True}) == '{"quit":true}'


def test_serialize_config_command() -> None:
    payload = config_payload(
        size_px=64,
        anchor="top_center",
        margin_px=20,
        offset_x=8,
        offset_y=8,
        accent="#7b2ff7",
        accent_secondary="#f97316",
        idle_opacity=0.6,
        fps=30,
    )
    line = serialize_command({"config": payload})
    parsed = parse_command(line)
    assert parsed["config"]["anchor"] == "top_center"
    assert parsed["config"]["accent_secondary"] == "#f97316"
    assert parsed["config"]["fps"] == 30


def test_parse_command_round_trip() -> None:
    original = {"level": 0.42, "show": True}
    assert parse_command(serialize_command(original)) == original


def test_config_payload_from_indicator_defaults() -> None:
    cfg = IndicatorConfig(strategy="pill")
    payload = config_payload(
        size_px=cfg.size_px,
        anchor=cfg.anchor,
        margin_px=cfg.margin_px,
        offset_x=cfg.offset_x,
        offset_y=cfg.offset_y,
        accent=cfg.orb_accent,
        accent_secondary=cfg.orb_accent_secondary,
        idle_opacity=cfg.orb_idle_opacity,
        fps=cfg.orb_fps,
    )
    assert payload["anchor"] == "top_center"
    assert payload["accent"] == "#7b2ff7"
    assert payload["accent_secondary"] == "#f97316"


class _FakeStdin(StringIO):
    def flush(self) -> None:
        return None


class _FakeProcess:
    def __init__(self) -> None:
        self.stdin = _FakeStdin()
        self.stdout = StringIO("ready\n")
        self.stderr = StringIO()
        self.pid = 4242
        self._returncode: int | None = None
        self.args: list[str] | None = None

    def poll(self) -> int | None:
        return self._returncode

    def wait(self, timeout: float | None = None) -> int:
        return 0 if self._returncode is None else self._returncode

    def kill(self) -> None:
        self._returncode = -9


@patch("sybl.indicator.pill_qt_win.subprocess.Popen")
def test_qt_pill_indicator_spawns_subprocess(mock_popen: MagicMock) -> None:
    fake = _FakeProcess()
    mock_popen.return_value = fake

    config = IndicatorConfig(strategy="pill", orb_fps=24, anchor="top_center")
    indicator = QtPillIndicator(config)
    assert not indicator.degraded

    indicator.show()
    assert not indicator.degraded
    mock_popen.assert_called_once()
    call_kwargs = mock_popen.call_args.kwargs
    assert call_kwargs["text"] is True
    assert mock_popen.call_args.args[0][-2:] == ["-m", "sybl.indicator.pill_qt"]

    written = fake.stdin.getvalue()
    lines = [line for line in written.splitlines() if line.strip()]
    assert len(lines) >= 1
    initial = json.loads(lines[0])
    assert initial["config"]["fps"] == 24
    assert initial["config"]["anchor"] == "top_center"

    indicator.update_level(0.8)
    indicator.set_phase("processing")
    indicator.hide()

    lines = [json.loads(line) for line in fake.stdin.getvalue().splitlines() if line]
    assert lines[1] == {"show": True, "phase": "listening"}
    assert lines[2] == {"level": 0.8}
    assert lines[3] == {"phase": "processing"}
    assert lines[4] == {"hide": True}

    indicator.shutdown()
    lines = [json.loads(line) for line in fake.stdin.getvalue().splitlines() if line]
    assert lines[-1] == {"quit": True}


@patch("sybl.indicator.pill_qt_win.subprocess.Popen")
def test_qt_pill_indicator_marks_degraded_when_spawn_fails(
    mock_popen: MagicMock,
) -> None:
    mock_popen.side_effect = OSError("spawn failed")

    indicator = QtPillIndicator(IndicatorConfig(strategy="pill"))
    indicator.show()
    assert indicator.degraded
    indicator.show()
    indicator.shutdown()


@patch("sybl.indicator.pill_qt_win.subprocess.Popen")
@patch("sybl.indicator.qt_available", return_value=True)
def test_create_indicator_orb_strategy_uses_wrapper(
    mock_qt: MagicMock,
    mock_popen: MagicMock,
) -> None:
    fake = _FakeProcess()
    mock_popen.return_value = fake

    config = SyblConfig(indicator=IndicatorConfig(strategy="pill"))
    with patch("sybl.indicator.sys.platform", "win32"):
        indicator = create_indicator(config)
    try:
        assert isinstance(indicator, QtPillIndicator)
        indicator.show()
        mock_popen.assert_called_once()
    finally:
        indicator.shutdown()


def test_strategy_orb_alias_normalizes_to_pill() -> None:
    cfg = IndicatorConfig(strategy="orb")  # type: ignore[arg-type]
    assert cfg.strategy == "pill"


@patch("sybl.indicator.pill_qt_win.subprocess.Popen", side_effect=OSError("no qt"))
@patch("sybl.indicator.qt_available", return_value=True)
def test_qt_pill_indicator_degraded_after_failed_show(
    mock_qt: MagicMock,
    mock_popen: MagicMock,
) -> None:
    indicator = QtPillIndicator(IndicatorConfig(strategy="pill"))
    assert not indicator.degraded
    indicator.show()
    assert indicator.degraded
    indicator.shutdown()
