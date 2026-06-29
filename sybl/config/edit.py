"""Open the sybl config file in the user's editor.

Shared by the ``sybl config edit`` CLI command and the TUI's ``e`` binding so
both surfaces resolve the editor and config path the same way.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

from sybl.config.manager import ConfigManager


class EditorError(Exception):
    """Raised when the config file cannot be opened in an editor."""


def ensure_config_file(manager: ConfigManager | None = None) -> Path:
    """Return the config path, writing a default file if it does not exist."""
    manager = manager or ConfigManager()
    if not manager.path.exists():
        manager.init()
    return manager.path


def resolve_editor_command(path: Path) -> list[str]:
    """Build the argv to open ``path`` in the user's preferred editor.

    Honors ``$VISUAL``/``$EDITOR`` (which may carry flags, e.g. ``code -w``)
    and falls back to a sensible per-platform default.
    """
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR")
    if editor:
        parts = shlex.split(editor, posix=os.name != "nt")
        if parts:
            return [*parts, str(path)]
    if sys.platform == "win32":
        return ["notepad.exe", str(path)]
    if sys.platform == "darwin":
        return ["open", "-t", str(path)]
    for candidate in ("nano", "vim", "vi"):
        if shutil.which(candidate):
            return [candidate, str(path)]
    return ["vi", str(path)]


def open_in_editor(path: Path) -> None:
    """Launch the editor on ``path`` and block until it exits."""
    command = resolve_editor_command(path)
    try:
        subprocess.run(command, check=False)  # noqa: S603 - editor argv is trusted
    except FileNotFoundError as exc:
        raise EditorError(
            f"Could not launch editor {command[0]!r}. "
            "Set $EDITOR (or $VISUAL) to your editor command."
        ) from exc
    except OSError as exc:
        raise EditorError(f"Failed to launch editor: {exc}") from exc
