"""Tests for logging setup and ring buffer."""

import logging
from pathlib import Path

from sybl.config import LoggingConfig
from sybl.logging import setup_logging
from sybl.logging.ring_buffer import RingBufferHandler


def test_ring_buffer_respects_maxlen() -> None:
    handler = RingBufferHandler(capacity=3)
    logger = logging.getLogger("test.ring_buffer")
    logger.handlers = [handler]
    logger.setLevel(logging.INFO)

    for index in range(5):
        logger.info("message-%s", index)

    recent = handler.get_recent()
    assert len(recent) == 3
    assert recent[0].message == "message-2"
    assert recent[-1].message == "message-4"


def test_setup_logging_writes_to_file(tmp_log_path: Path) -> None:
    config = LoggingConfig(level="INFO", ring_buffer_size=10)
    ring_handler = setup_logging(config, log_file=tmp_log_path)

    logger = logging.getLogger("sybl.test")
    logger.info("hello from test")

    assert tmp_log_path.exists()
    contents = tmp_log_path.read_text(encoding="utf-8")
    assert "hello from test" in contents

    recent = ring_handler.get_recent(1)
    assert recent[-1].message == "hello from test"
