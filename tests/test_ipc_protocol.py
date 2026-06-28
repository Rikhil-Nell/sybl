"""Tests for IPC protocol encoding."""

from __future__ import annotations

import pytest

from sybl.ipc.protocol import (
    CommandName,
    CommandResponse,
    decode_line,
    encode_line,
    parse_command_request,
)


def test_encode_decode_roundtrip() -> None:
    payload = {"id": "abc", "command": "ping", "params": {}}
    line = encode_line(payload)
    assert decode_line(line) == payload


def test_parse_command_request() -> None:
    line = encode_line({"id": "1", "command": "get_status", "params": {}})
    request = parse_command_request(line)
    assert request.id == "1"
    assert request.command is CommandName.GET_STATUS


def test_command_response_model() -> None:
    response = CommandResponse(id="1", ok=True, result={"pong": True})
    payload = encode_line(response.model_dump(mode="json"))
    restored = CommandResponse.model_validate(decode_line(payload))
    assert restored.ok is True
    assert restored.result == {"pong": True}


def test_parse_invalid_command_raises() -> None:
    with pytest.raises(ValueError):
        parse_command_request(b"not json\n")
