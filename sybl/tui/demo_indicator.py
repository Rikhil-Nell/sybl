"""Drive the capture overlay during ``sybl tui --demo``."""

from __future__ import annotations

import logging

from sybl.config.models import SyblConfig
from sybl.indicator import create_indicator
from sybl.indicator.base import CaptureIndicator

logger = logging.getLogger("sybl.tui.demo_indicator")


class DemoIndicatorBridge:
    """Mirror daemon indicator show/hide/level wiring for demo mode."""

    def __init__(self, config: SyblConfig) -> None:
        self._indicator: CaptureIndicator | None = None
        ind = config.indicator
        if not ind.enabled or ind.strategy == "none":
            logger.info("Demo indicator disabled (strategy=%s)", ind.strategy)
            return

        self._indicator = create_indicator(config)
        impl = type(self._indicator).__name__
        if getattr(self._indicator, "degraded", False):
            logger.warning(
                "Demo indicator failed to start (strategy=%s, implementation=%s)",
                ind.strategy,
                impl,
            )
            self._indicator = None
            return

        logger.info(
            "Demo indicator active (strategy=%s, implementation=%s)",
            ind.strategy,
            impl,
        )

    @property
    def active(self) -> bool:
        return self._indicator is not None

    def on_state(self, state: str) -> None:
        if self._indicator is None:
            return
        if state == "listening":
            self._indicator.show()
        elif state in ("processing", "injecting"):
            self._indicator.set_phase("processing")
        elif state in ("idle", "offline", "error", "cancelled"):
            self._indicator.hide()

    def on_level(self, value: float) -> None:
        if self._indicator is not None:
            self._indicator.update_level(value)

    def shutdown(self) -> None:
        if self._indicator is None:
            return
        self._indicator.shutdown()
        self._indicator = None
