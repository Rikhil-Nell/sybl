"""No-op capture indicator for tests and unsupported platforms."""

from __future__ import annotations


class NoOpIndicator:
    def show(self) -> None:
        return None

    def hide(self) -> None:
        return None

    def update_level(self, level: float) -> None:
        return None

    def set_phase(self, phase: str) -> None:  # noqa: ARG002
        return None

    def shutdown(self) -> None:
        return None
