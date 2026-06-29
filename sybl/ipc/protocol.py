"""NDJSON IPC protocol types."""

from __future__ import annotations

import json
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, ValidationError


class CommandName(StrEnum):
    PING = "ping"
    GET_STATUS = "get_status"
    GET_CONFIG = "get_config"
    PATCH_CONFIG = "patch_config"
    LIST_PROVIDER_KEYS = "list_provider_keys"
    SET_PROVIDER_KEY = "set_provider_key"
    GET_LOGS = "get_logs"
    GET_HISTORY = "get_history"
    LIST_SOUNDS = "list_sounds"
    IMPORT_SOUND = "import_sound"
    CLEAR_SOUND = "clear_sound"
    SHUTDOWN = "shutdown"


class CommandRequest(BaseModel):
    id: str
    command: CommandName
    params: dict[str, Any] = Field(default_factory=dict)


class CommandResponse(BaseModel):
    id: str
    ok: bool
    result: dict[str, Any] | None = None
    error: str | None = None


class EventHello(BaseModel):
    type: str = "hello"
    token: str


class DaemonInfo(BaseModel):
    pid: int
    host: str
    command_port: int
    event_port: int
    token: str


def encode_line(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, separators=(",", ":")) + "\n").encode("utf-8")


def decode_line(line: bytes | str) -> dict[str, Any]:
    text = line.decode("utf-8") if isinstance(line, bytes) else line
    text = text.strip()
    if not text:
        raise ValueError("Empty line")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("Expected JSON object")
    return data


def parse_command_request(line: bytes | str) -> CommandRequest:
    try:
        return CommandRequest.model_validate(decode_line(line))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"Invalid command request: {exc}") from exc


def parse_event_hello(line: bytes | str) -> EventHello:
    try:
        return EventHello.model_validate(decode_line(line))
    except (ValidationError, ValueError) as exc:
        raise ValueError(f"Invalid event hello: {exc}") from exc
