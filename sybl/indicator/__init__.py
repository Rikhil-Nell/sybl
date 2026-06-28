"""On-screen capture indicator while dictating."""

from __future__ import annotations

import sys

from sybl.config.models import SyblConfig
from sybl.indicator.base import CaptureIndicator
from sybl.indicator.noop import NoOpIndicator

__all__ = ["CaptureIndicator", "NoOpIndicator", "create_indicator"]


def create_indicator(config: SyblConfig) -> CaptureIndicator:
    indicator = config.indicator
    if not indicator.enabled or indicator.strategy == "none":
        return NoOpIndicator()
    if sys.platform == "win32" and indicator.strategy == "overlay":
        from sybl.indicator.tk_win import TkCaptureIndicator

        return TkCaptureIndicator(indicator)
    return NoOpIndicator()
