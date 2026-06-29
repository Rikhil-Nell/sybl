"""Native WAV file picker for the TUI (Windows tkinter fallback)."""

from __future__ import annotations

import sys
from pathlib import Path


def browse_wav_file(*, title: str = "Select WAV sound cue") -> Path | None:
    """Open a file picker dialog; returns None when cancelled or unavailable."""

    def _pick() -> Path | None:
        if sys.platform != "win32":
            return None
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        try:
            selected = filedialog.askopenfilename(
                title=title,
                filetypes=[("WAV audio", "*.wav"), ("All files", "*.*")],
            )
        finally:
            root.destroy()
        if not selected:
            return None
        return Path(selected)

    return _pick()
