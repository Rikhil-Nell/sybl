"""Windows tkinter overlay capture indicator."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from dataclasses import dataclass
from enum import Enum, auto

from sybl.config.models import IndicatorConfig
from sybl.indicator.cursor_win import clamp_to_screen, get_cursor_pos

logger = logging.getLogger("sybl.indicator.tk")


class _CmdKind(Enum):
    SHOW = auto()
    HIDE = auto()
    LEVEL = auto()


@dataclass(frozen=True)
class _Command:
    kind: _CmdKind
    level: float = 0.0
    x: int = 0
    y: int = 0


class TkCaptureIndicator:
    """Thread-safe tkinter pill shown near the cursor while listening."""

    def __init__(self, config: IndicatorConfig) -> None:
        self._config = config
        self._commands: queue.Queue[_Command | None] = queue.Queue()
        self._ready = threading.Event()
        self._failed = threading.Event()
        self._stopped = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="sybl-indicator",
            daemon=False,
        )
        self._thread.start()
        if not self._ready.wait(timeout=5.0) and self._failed.is_set():
            logger.warning(
                "Capture indicator failed to initialize; continuing without overlay"
            )

    @property
    def degraded(self) -> bool:
        return self._failed.is_set()

    def show(self) -> None:
        if self._failed.is_set():
            return
        x, y = get_cursor_pos()
        x += self._config.offset_x
        y += self._config.offset_y
        x, y = clamp_to_screen(x, y, self._config.size_px, self._bar_height())
        self._commands.put(_Command(_CmdKind.SHOW, x=x, y=y))

    def hide(self) -> None:
        if self._failed.is_set():
            return
        self._commands.put(_Command(_CmdKind.HIDE))

    def update_level(self, level: float) -> None:
        if self._failed.is_set():
            return
        clamped = max(0.0, min(1.0, level))
        self._commands.put(_Command(_CmdKind.LEVEL, level=clamped))

    def shutdown(self) -> None:
        if self._failed.is_set():
            return
        self._commands.put(None)
        self._stopped.wait(timeout=2.0)
        self._thread.join(timeout=2.0)

    def _bar_height(self) -> int:
        return max(16, self._config.size_px // 3)

    def _run(self) -> None:
        try:
            root = tk.Tk()
            root.withdraw()

            size = self._config.size_px
            bar_h = self._bar_height()
            window = tk.Toplevel(root)
            window.overrideredirect(True)
            window.attributes("-topmost", True)
            window.configure(bg="#1a1a1a")
            window.geometry(f"{size}x{bar_h}")

            canvas = tk.Canvas(
                window,
                width=size,
                height=bar_h,
                highlightthickness=0,
                bg="#1a1a1a",
            )
            canvas.pack(fill=tk.BOTH, expand=True)

            border = canvas.create_rectangle(
                2,
                2,
                size - 2,
                bar_h - 2,
                outline="#4ade80",
                width=2,
            )
            level_bar = canvas.create_rectangle(
                4,
                4,
                4,
                bar_h - 4,
                fill="#4ade80",
                outline="",
            )
            canvas.create_oval(
                4,
                (bar_h // 2) - 3,
                10,
                (bar_h // 2) + 3,
                fill="#4ade80",
                outline="",
            )

            visible = False
            after_id: str | None = None
            self._ready.set()

            def apply_command(cmd: _Command) -> None:
                nonlocal visible
                if cmd.kind is _CmdKind.SHOW:
                    window.geometry(f"{size}x{bar_h}+{cmd.x}+{cmd.y}")
                    window.deiconify()
                    visible = True
                elif cmd.kind is _CmdKind.HIDE:
                    window.withdraw()
                    visible = False
                elif cmd.kind is _CmdKind.LEVEL and visible:
                    fill_width = 4 + int((size - 8) * cmd.level)
                    canvas.coords(level_bar, 4, 4, fill_width, bar_h - 4)
                    canvas.itemconfig(border, outline="#4ade80")

            def pump_queue() -> None:
                nonlocal after_id
                while True:
                    try:
                        cmd = self._commands.get_nowait()
                    except queue.Empty:
                        break
                    if cmd is None:
                        if after_id is not None:
                            root.after_cancel(after_id)
                            after_id = None

                        def shutdown_ui() -> None:
                            window.withdraw()
                            try:
                                window.destroy()
                            except tk.TclError:
                                pass
                            root.quit()

                        root.after(0, shutdown_ui)
                        return
                    apply_command(cmd)
                after_id = root.after(30, pump_queue)

            pump_queue()
            root.mainloop()
            try:
                root.destroy()
            except tk.TclError:
                pass
        except Exception:
            logger.exception("Capture indicator thread failed")
            self._failed.set()
            self._ready.set()
        finally:
            self._stopped.set()
