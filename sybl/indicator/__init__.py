"""On-screen capture indicator while dictating."""

from __future__ import annotations

import logging
import sys

from sybl.config.models import SyblConfig
from sybl.indicator.base import CaptureIndicator
from sybl.indicator.noop import NoOpIndicator
from sybl.indicator.sound import IndicatorSoundCue, create_sound_cue

logger = logging.getLogger("sybl.indicator")

__all__ = [
    "CaptureIndicator",
    "IndicatorSoundCue",
    "NoOpIndicator",
    "create_indicator",
    "create_sound_cue",
    "qt_available",
]


def qt_available() -> bool:
    """Return True when PySide6 is installed (does not import Qt)."""
    import importlib.util

    return importlib.util.find_spec("PySide6") is not None


def _try_pill_indicator(config: SyblConfig) -> CaptureIndicator | None:
    if not qt_available():
        logger.warning(
            "indicator.strategy=pill requires PySide6; install with: uv tool install "
            "'sybl[pill]' (or pip install 'sybl[pill]')"
        )
        return None

    if sys.platform != "win32":
        logger.warning("Qt pill overlay is Windows-only in this release")
        return None

    from sybl.indicator.pill_qt_win import QtPillIndicator

    indicator = QtPillIndicator(config.indicator)
    logger.info("Qt pill overlay ready (lazy spawn on listen)")
    return indicator


def _try_tk_indicator(config: SyblConfig) -> CaptureIndicator | None:
    if sys.platform != "win32":
        return None
    from sybl.indicator.tk_win import TkCaptureIndicator

    return TkCaptureIndicator(config.indicator)


def create_indicator(config: SyblConfig) -> CaptureIndicator:
    indicator = config.indicator
    if not indicator.enabled or indicator.strategy == "none":
        logger.info("Capture indicator disabled (strategy=%s)", indicator.strategy)
        return NoOpIndicator()

    if indicator.strategy == "pill":
        pill = _try_pill_indicator(config)
        if pill is not None:
            logger.info("Capture indicator using Qt pill overlay")
            return pill
        tk = _try_tk_indicator(config)
        if tk is not None:
            logger.info("Capture indicator falling back to tk overlay")
            return tk
        logger.warning("Capture indicator unavailable; using no-op")
        return NoOpIndicator()

    if sys.platform == "win32" and indicator.strategy == "overlay":
        tk = _try_tk_indicator(config)
        if tk is not None:
            logger.info("Capture indicator using tk overlay")
            return tk
    logger.info("Capture indicator using no-op (strategy=%s)", indicator.strategy)
    return NoOpIndicator()
