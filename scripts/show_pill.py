#!/usr/bin/env python3
"""Qt pill smoke test — no daemon, no config, no sybl CLI.

Spawns the pill subprocess, slides it down, animates wave bars, switches to
spinner, then slides up. Press Ctrl+C to quit early.

Usage:
    uv run python scripts/show_pill.py
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
import time
from pathlib import Path


def main() -> int:
    try:
        import PySide6  # noqa: F401
    except ImportError:
        print("PySide6 not installed. Reinstall sybl from PyPI.", file=sys.stderr)
        return 1

    root = Path(__file__).resolve().parents[1]
    print("  sybl Qt pill smoke test")
    print("  Hold Ctrl+C to quit.\n")

    executable = sys.executable
    if sys.platform == "win32" and executable.lower().endswith("pythonw.exe"):
        python = Path(executable).with_name("python.exe")
        if python.is_file():
            executable = str(python)

    popen_kwargs: dict[str, object] = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "bufsize": 1,
        "cwd": str(root),
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]

    process = subprocess.Popen(
        [executable, "-m", "sybl.indicator.pill_qt"],
        **popen_kwargs,  # type: ignore[arg-type]
    )
    if process.stdin is None or process.stdout is None:
        print("Failed to open pill subprocess pipes", file=sys.stderr)
        return 1

    def send(payload: dict) -> None:
        assert process.stdin is not None
        process.stdin.write(json.dumps(payload, separators=(",", ":")) + "\n")
        process.stdin.flush()

    send(
        {
            "config": {
                "margin_px": 0,
                "accent": "#7b2ff7",
                "accent_secondary": "#f97316",
            }
        }
    )
    line = process.stdout.readline().strip()
    if line != "ready":
        err = process.stderr.read() if process.stderr is not None else ""
        print(f"Pill failed to start: {line or err}", file=sys.stderr)
        process.kill()
        return 1

    send({"show": True})
    start = time.monotonic()
    try:
        while process.poll() is None:
            t = time.monotonic() - start
            if t < 3.0:
                level = 0.2 + 0.5 * (1.0 + math.sin(t * 5.0)) / 2.0
                send({"level": level})
            elif t < 5.5:
                send({"phase": "processing"})
            else:
                send({"hide": True})
                time.sleep(0.5)
                break
            time.sleep(1.0 / 30.0)
    except KeyboardInterrupt:
        print()
    finally:
        send({"quit": True})
        process.wait(timeout=2.0)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
