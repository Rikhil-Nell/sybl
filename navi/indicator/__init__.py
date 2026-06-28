"""On-screen capture indicator while dictating."""

from __future__ import annotations

import sys

from navi.config.models import NaviConfig
from navi.indicator.base import CaptureIndicator
from navi.indicator.noop import NoOpIndicator

__all__ = ["CaptureIndicator", "NoOpIndicator", "create_indicator"]


def create_indicator(config: NaviConfig) -> CaptureIndicator:
    indicator = config.indicator
    if not indicator.enabled or indicator.strategy == "none":
        return NoOpIndicator()
    if sys.platform == "win32" and indicator.strategy == "overlay":
        from navi.indicator.tk_win import TkCaptureIndicator

        return TkCaptureIndicator(indicator)
    return NoOpIndicator()
