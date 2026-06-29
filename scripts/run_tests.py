#!/usr/bin/env python3
"""Hermetic test runner with CI-parity environment."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> None:
    print("+", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=ROOT, env=env, check=True)


def main(argv: list[str] | None = None) -> int:
    args = list(argv or sys.argv[1:])
    with tempfile.TemporaryDirectory(prefix="sybl-test-") as tmp:
        tmp_path = Path(tmp)
        config_dir = tmp_path / "config"
        state_dir = tmp_path / "state"
        config_dir.mkdir()
        state_dir.mkdir()

        env = os.environ.copy()
        env.setdefault("TZ", "UTC")
        env.setdefault("LANG", "C.UTF-8")
        env.setdefault("NO_COLOR", "1")
        env.setdefault("TERM", "dumb")
        env["SYBL_CONFIG_DIR"] = str(config_dir)
        env["SYBL_STATE_DIR"] = str(state_dir)

        if sys.platform.startswith("linux"):
            env.setdefault(
                "PYTHON_KEYRING_BACKEND",
                "keyrings.alt.file.PlaintextKeyring",
            )

        _run(["uv", "sync"], env=env)

        if sys.platform.startswith("linux"):
            _run(["uv", "pip", "install", "keyrings.alt"], env=env)

        _run(["uv", "run", "ruff", "check", "sybl", "tests"], env=env)

        pytest_cmd = [
            "uv",
            "run",
            "pytest",
            "-m",
            "not integration",
            "-q",
            *args,
        ]
        if sys.platform.startswith("linux"):
            pytest_cmd.extend(["--ignore=tests/test_inject.py"])
            xvfb = shutil.which("xvfb-run")
            if xvfb:
                pytest_cmd = [xvfb, *pytest_cmd]
        _run(pytest_cmd, env=env)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
