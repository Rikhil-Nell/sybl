"""Qt dock pill overlay host — QQuickView + stdin NDJSON control."""

from __future__ import annotations

import json
import logging
import queue
import sys
import threading
from pathlib import Path
from typing import Any

from sybl.indicator.protocol import parse_command

logger = logging.getLogger("sybl.indicator.pill_qt")

_PILL_QML = Path(__file__).resolve().parent / "Pill.qml"
_PILL_HEIGHT = 44
_HIDDEN_OFFSET = 24
_DEFAULT_PILL_WIDTH = 280
_TOP_BLEED_PX = 1
_HIDE_ANIMATION_MS = 400


def _js_literal(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=True)


class _PillHost:
    def __init__(self) -> None:
        self._app = None
        self._view = None
        self._root = None
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._pending: list[dict[str, Any]] = []
        self._pending_lock = threading.Lock()
        self._hide_timer = None
        self._command_queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._config: dict[str, Any] = {
            "size_px": 72,
            "anchor": "top_center",
            "margin_px": 0,
            "offset_x": 16,
            "offset_y": 16,
            "accent": "#7b2ff7",
            "accent_secondary": "#f97316",
            "idle_opacity": 0.55,
            "fps": 30,
        }

    def _screen_at_cursor(self):
        from PySide6.QtGui import QCursor, QGuiApplication

        screen = QGuiApplication.screenAt(QCursor.pos())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen

    def _sync_view_size(self) -> None:
        if self._view is None or self._root is None:
            return
        margin = int(self._config.get("margin_px", 0))
        width = int(self._root.property("width") or _DEFAULT_PILL_WIDTH)
        height = _PILL_HEIGHT + _HIDDEN_OFFSET + margin
        self._view.setWidth(width)
        self._view.setHeight(height)

    def _position_window(self) -> None:
        if self._view is None or self._app is None:
            return

        screen = self._screen_at_cursor()
        if screen is None:
            return

        margin = int(self._config.get("margin_px", 0))
        geo = screen.geometry()
        width = self._view.width()
        height = self._view.height()
        x = geo.x() + (geo.width() - width) // 2
        bleed = _TOP_BLEED_PX if margin == 0 else 0
        y = geo.y() + margin - bleed
        self._view.setGeometry(x, y, width, height)

    def _apply_config(self, config: dict[str, Any]) -> None:
        self._config.update(config)
        root = self._root
        if root is None:
            return
        margin = int(self._config.get("margin_px", 0))
        root.setProperty("marginPx", margin)
        root.setProperty("accent", str(self._config.get("accent", "#7b2ff7")))
        root.setProperty(
            "accentSecondary",
            str(self._config.get("accent_secondary", "#f97316")),
        )
        self._sync_view_size()
        self._position_window()

    def _apply_command(self, message: dict[str, Any]) -> None:
        if "quit" in message:
            self._stop.set()
            if self._app is not None:
                self._app.quit()
            return
        if "config" in message and isinstance(message["config"], dict):
            self._apply_config(message["config"])
        if "phase" in message:
            phase = str(message["phase"])
            if self._root is not None:
                self._root.setProperty("phase", phase)
        if message.get("show"):
            if self._root is not None:
                self._root.setProperty("phase", "listening")
                self._root.setProperty("slideVisible", True)
            self._sync_view_size()
            self._position_window()
            if self._view is not None:
                self._view.show()
                self._enable_click_through()
        if message.get("hide"):
            self._schedule_hide()
        if "level" in message:
            level = float(message["level"])
            if self._root is not None:
                self._root.setProperty("level", level)

    def _schedule_hide(self) -> None:
        from PySide6.QtCore import QTimer

        if self._root is not None:
            self._root.setProperty("slideVisible", False)
        if self._hide_timer is not None:
            self._hide_timer.stop()
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._finish_hide)
        self._hide_timer.start(_HIDE_ANIMATION_MS)

    def _finish_hide(self) -> None:
        if self._view is not None:
            self._view.hide()

    def _stdin_loop(self) -> None:
        for raw in sys.stdin:
            if self._stop.is_set():
                break
            line = raw.strip()
            if not line:
                continue
            try:
                message = parse_command(line)
            except Exception:
                logger.exception("Invalid pill command: %r", line)
                continue
            if not self._ready.is_set():
                with self._pending_lock:
                    self._pending.append(message)
            else:
                self._command_queue.put(message)
            if "quit" in message:
                break

    def _drain_command_queue(self) -> None:
        while True:
            try:
                message = self._command_queue.get_nowait()
            except queue.Empty:
                break
            self._apply_command(message)
        if not self._stop.is_set():
            from PySide6.QtCore import QTimer

            QTimer.singleShot(10, self._drain_command_queue)

    def _enable_click_through(self) -> None:
        if sys.platform != "win32" or self._view is None:
            return
        try:
            import ctypes

            hwnd = int(self._view.winId())
            gwl_exstyle = -20
            ws_ex_layered = 0x00080000
            ws_ex_transparent = 0x00000020
            ws_ex_toolwindow = 0x00000080
            user32 = ctypes.windll.user32
            style = user32.GetWindowLongW(hwnd, gwl_exstyle)
            user32.SetWindowLongW(
                hwnd,
                gwl_exstyle,
                style | ws_ex_layered | ws_ex_transparent | ws_ex_toolwindow,
            )
        except Exception:
            logger.exception("Failed to enable click-through")

    def _on_loaded(self) -> None:
        root = self._view.rootObject() if self._view is not None else None
        if root is None:
            logger.error("Pill QML root object missing")
            self._stop.set()
            if self._app is not None:
                self._app.quit()
            return
        self._root = root
        self._apply_config(dict(self._config))
        with self._pending_lock:
            pending = list(self._pending)
            self._pending.clear()
        for message in pending:
            self._apply_command(message)
        self._ready.set()
        self._drain_command_queue()
        print("ready", flush=True)
        logger.info("Qt pill overlay ready")

    def run(self) -> int:
        if not _PILL_QML.is_file():
            logger.error("Missing QML: %s", _PILL_QML)
            return 1

        from PySide6.QtCore import Qt, QTimer, QUrl
        from PySide6.QtGui import QColor, QGuiApplication
        from PySide6.QtQuick import QQuickView

        self._app = QGuiApplication(sys.argv)
        self._view = QQuickView()
        self._view.setResizeMode(QQuickView.SizeRootObjectToView)
        self._view.setColor(QColor(0, 0, 0, 0))
        self._view.setFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
            | Qt.WindowDoesNotAcceptFocus
        )
        self._view.setSource(QUrl.fromLocalFile(str(_PILL_QML.resolve())))
        for error in self._view.errors():
            logger.error("QML load error: %s", error.toString())
        self._view.setWidth(_DEFAULT_PILL_WIDTH)
        self._view.setHeight(_PILL_HEIGHT + _HIDDEN_OFFSET)
        self._position_window()
        self._view.hide()

        reader = threading.Thread(
            target=self._stdin_loop,
            name="sybl-pill-stdin",
            daemon=True,
        )
        reader.start()

        QTimer.singleShot(0, self._on_loaded)
        exit_code = self._app.exec()
        self._stop.set()
        reader.join(timeout=1.0)
        return exit_code


def main() -> int:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    return _PillHost().run()
