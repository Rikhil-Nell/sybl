"""Session state machine for dictation lifecycle."""

from __future__ import annotations

import logging
from enum import StrEnum

logger = logging.getLogger("sybl.core.state")


class SessionState(StrEnum):
    IDLE = "idle"
    LISTENING = "listening"
    PROCESSING = "processing"
    INJECTING = "injecting"
    CANCELLED = "cancelled"
    ERROR = "error"


_VALID_TRANSITIONS: dict[SessionState, set[SessionState]] = {
    SessionState.IDLE: {
        SessionState.LISTENING,
        SessionState.CANCELLED,
        SessionState.ERROR,
    },
    SessionState.LISTENING: {
        SessionState.PROCESSING,
        SessionState.CANCELLED,
        SessionState.ERROR,
        SessionState.IDLE,
    },
    SessionState.PROCESSING: {
        SessionState.IDLE,
        SessionState.INJECTING,
        SessionState.ERROR,
        SessionState.CANCELLED,
    },
    SessionState.INJECTING: {
        SessionState.IDLE,
        SessionState.ERROR,
        SessionState.CANCELLED,
    },
    SessionState.CANCELLED: {SessionState.IDLE},
    SessionState.ERROR: {SessionState.IDLE},
}


class InvalidTransitionError(Exception):
    """Raised when a state transition is not allowed."""


class StateMachine:
    def __init__(self, initial: SessionState = SessionState.IDLE) -> None:
        self._state = initial

    @property
    def state(self) -> SessionState:
        return self._state

    def transition(self, to: SessionState) -> None:
        allowed = _VALID_TRANSITIONS.get(self._state, set())
        if to not in allowed:
            raise InvalidTransitionError(
                f"Invalid transition: {self._state.value} -> {to.value}"
            )
        logger.debug("State transition: %s -> %s", self._state.value, to.value)
        self._state = to

    def reset(self) -> None:
        self._state = SessionState.IDLE
