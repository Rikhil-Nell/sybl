"""Capture indicator interface."""

from __future__ import annotations

from typing import Protocol


class CaptureIndicator(Protocol):
    def show(self) -> None: ...

    def hide(self) -> None: ...

    def update_level(self, level: float) -> None: ...

    def shutdown(self) -> None: ...
