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
            "Qt listening pill requires PySide6; reinstall sybl from PyPI "
            "(uv tool install sybl / pipx install sybl)"
        )
        return None

    if sys.platform != "win32":
        logger.warning("Qt listening pill is Windows-only in this release")
        return None

    from sybl.indicator.pill_qt_win import QtPillIndicator

    indicator = QtPillIndicator(config.indicator)
    logger.info("Qt listening pill ready (lazy spawn on listen)")
    return indicator


def create_indicator(config: SyblConfig) -> CaptureIndicator:
    indicator = config.indicator
    if not indicator.enabled or indicator.strategy == "none":
        logger.info("Capture indicator disabled (strategy=%s)", indicator.strategy)
        return NoOpIndicator()

    pill = _try_pill_indicator(config)
    if pill is not None:
        logger.info("Capture indicator using Qt listening pill")
        return pill

    logger.warning("Capture indicator unavailable; using no-op")
    return NoOpIndicator()
