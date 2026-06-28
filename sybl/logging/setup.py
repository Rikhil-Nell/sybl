"""Configure structured logging for sybl."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from sybl.config.models import LoggingConfig
from sybl.logging.ring_buffer import RingBufferHandler

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"


def setup_logging(
    config: LoggingConfig,
    *,
    log_file: Path,
    verbose: bool = False,
) -> RingBufferHandler:
    level_name = "DEBUG" if verbose else config.level.upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(level)

    formatter = logging.Formatter(LOG_FORMAT)

    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root.addHandler(file_handler)

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root.addHandler(console_handler)

    ring_handler = RingBufferHandler(config.ring_buffer_size)
    ring_handler.setFormatter(formatter)
    ring_handler.setLevel(level)
    root.addHandler(ring_handler)

    logging.getLogger("sybl").debug(
        "Logging initialized (level=%s, file=%s)", level_name, log_file
    )
    return ring_handler
