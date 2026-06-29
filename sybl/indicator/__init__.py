"""On-screen capture indicator while dictating."""

from __future__ import annotations

import sys

from sybl.config.models import SyblConfig
from sybl.indicator.base import CaptureIndicator
from sybl.indicator.noop import NoOpIndicator
from sybl.indicator.sound import IndicatorSoundCue, create_sound_cue

__all__ = [
    "CaptureIndicator",
    "IndicatorSoundCue",
    "NoOpIndicator",
    "create_indicator",
    "create_sound_cue",
]


def create_indicator(config: SyblConfig) -> CaptureIndicator:
    indicator = config.indicator
    if not indicator.enabled or indicator.strategy == "none":
        return NoOpIndicator()
    if sys.platform == "win32" and indicator.strategy == "overlay":
        from sybl.indicator.tk_win import TkCaptureIndicator

        return TkCaptureIndicator(indicator)
    return NoOpIndicator()
