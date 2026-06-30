"""Qt pill overlay wrapper — spawns the PySide6 subprocess."""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from sybl.config.models import IndicatorConfig
from sybl.indicator.base import IndicatorPhase
from sybl.indicator.protocol import config_payload, serialize_command

logger = logging.getLogger("sybl.indicator.pill_qt_win")


class QtPillIndicator:
    """CaptureIndicator backed by a separate Qt QML overlay process."""

    def __init__(self, config: IndicatorConfig) -> None:
        self._config = config
        self._process: subprocess.Popen[str] | None = None
        self._failed = False
        self._lock = threading.Lock()

    @property
    def degraded(self) -> bool:
        return self._failed

    @staticmethod
    def _gui_executable() -> str:
        executable = sys.executable
        if sys.platform == "win32" and executable.lower().endswith("pythonw.exe"):
            python = Path(executable).with_name("python.exe")
            if python.is_file():
                return str(python)
        return executable

    def show(self) -> None:
        if not self._ensure_spawned():
            return
        self._send({"show": True, "phase": "listening"})

    def hide(self) -> None:
        if self._process is None:
            return
        self._send({"hide": True})

    def update_level(self, level: float) -> None:
        if self._process is None:
            return
        clamped = max(0.0, min(1.0, level))
        self._send({"level": clamped})

    def set_phase(self, phase: IndicatorPhase) -> None:
        if self._process is None:
            return
        self._send({"phase": phase})

    def shutdown(self) -> None:
        with self._lock:
            process = self._process
            if process is None:
                return
            try:
                if process.stdin is not None:
                    process.stdin.write(serialize_command({"quit": True}) + "\n")
                    process.stdin.flush()
            except OSError:
                pass
            try:
                process.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=1.0)
            finally:
                self._process = None

    def _config_dict(self) -> dict[str, Any]:
        anchor = self._config.anchor
        if anchor not in ("top_center", "cursor"):
            anchor = "top_center"
        return config_payload(
            size_px=self._config.size_px,
            anchor=anchor,
            margin_px=self._config.margin_px,
            offset_x=self._config.offset_x,
            offset_y=self._config.offset_y,
            accent=self._config.orb_accent,
            accent_secondary=self._config.orb_accent_secondary,
            idle_opacity=self._config.orb_idle_opacity,
            fps=self._config.orb_fps,
        )

    def _ensure_spawned(self) -> bool:
        if self._failed:
            return False
        if self._process is not None and self._process.poll() is None:
            return True
        try:
            self._spawn()
        except Exception:
            logger.exception("Qt pill overlay failed to start")
            self._failed = True
            self._process = None
            return False
        return self._process is not None and self._process.poll() is None

    def _spawn(self) -> None:
        popen_kwargs: dict[str, object] = {
            "stdin": subprocess.PIPE,
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
            "text": True,
            "bufsize": 1,
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        process = subprocess.Popen(
            [self._gui_executable(), "-m", "sybl.indicator.pill_qt"],
            **popen_kwargs,  # type: ignore[arg-type]
        )
        if process.stdin is None or process.stdout is None:
            process.kill()
            raise RuntimeError("pill_qt subprocess pipes unavailable")
        self._process = process
        if process.stderr is not None:
            threading.Thread(
                target=self._drain_stderr,
                args=(process.stderr,),
                name="sybl-pill-qt-stderr",
                daemon=True,
            ).start()
        initial = serialize_command({"config": self._config_dict()}) + "\n"
        process.stdin.write(initial)
        process.stdin.flush()
        try:
            line = process.stdout.readline()
        except OSError as exc:
            raise RuntimeError("pill_qt subprocess stdout unavailable") from exc
        if process.poll() is not None or line.strip() != "ready":
            stderr = ""
            if process.stderr is not None:
                stderr = process.stderr.read()
            detail = stderr.strip() or line.strip() or "unknown startup failure"
            raise RuntimeError(f"pill_qt subprocess failed to start: {detail}")
        logger.info("Qt pill subprocess started (pid=%s)", process.pid)

    def _drain_stderr(self, stream) -> None:  # noqa: ANN001
        try:
            for line in stream:
                text = line.rstrip()
                if text:
                    logger.warning("pill_qt subprocess: %s", text)
        except OSError:
            pass

    def _send(self, command: dict[str, Any]) -> None:
        if self._failed:
            return
        with self._lock:
            process = self._process
            if process is None or process.stdin is None:
                return
            if process.poll() is not None:
                logger.warning("Qt pill subprocess exited unexpectedly")
                self._failed = True
                self._process = None
                return
            try:
                line = serialize_command(command) + "\n"
                process.stdin.write(line)
                process.stdin.flush()
            except OSError:
                logger.warning("Lost connection to Qt pill subprocess")
                self._failed = True
