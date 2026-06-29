#!/usr/bin/env python3
"""Flag Unix-only patterns in changed Python files."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("fcntl", re.compile(r"\bimport fcntl\b|\bfrom fcntl\b")),
    ("termios", re.compile(r"\bimport termios\b|\bfrom termios\b")),
    ("os.setsid", re.compile(r"\bos\.setsid\s*\(")),
    ("os.kill(pid, 0)", re.compile(r"\bos\.kill\s*\([^,]+,\s*0\s*\)")),
    ('hardcoded "/tmp"', re.compile(r'["\']/tmp/')),
    ("signal.SIGKILL", re.compile(r"\bsignal\.SIGKILL\b")),
]

SKIP_SUFFIX = "# unixism-ok:"


def _changed_files() -> list[Path]:
    try:
        base = subprocess.check_output(
            ["git", "merge-base", "HEAD", "origin/main"],
            cwd=ROOT,
            text=True,
        ).strip()
    except subprocess.CalledProcessError:
        base = "HEAD~1"
    out = subprocess.check_output(
        ["git", "diff", "--name-only", base, "HEAD"],
        cwd=ROOT,
        text=True,
    )
    files: list[Path] = []
    for line in out.splitlines():
        path = Path(line.strip())
        if path.suffix == ".py" and path.parts and path.parts[0] in ("sybl", "tests"):
            files.append(path)
    return files


def _scan_file(path: Path) -> list[str]:
    hits: list[str] = []
    text = path.read_text(encoding="utf-8")
    for lineno, line in enumerate(text.splitlines(), start=1):
        if SKIP_SUFFIX in line:
            continue
        for label, pattern in PATTERNS:
            if pattern.search(line):
                hits.append(f"{path}:{lineno}: {label} — {line.strip()}")
    return hits


def main() -> int:
    files = _changed_files()
    if not files:
        print("No changed sybl/ or tests/ Python files to scan.")
        return 0

    all_hits: list[str] = []
    for path in files:
        full = ROOT / path
        if full.is_file():
            all_hits.extend(_scan_file(full))

    if all_hits:
        print("Unix-only patterns found (use '# unixism-ok: reason' to allow):\n")
        print("\n".join(all_hits))
        return 1

    print(f"Scanned {len(files)} file(s); no unixisms found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
