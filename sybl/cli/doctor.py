"""`sybl doctor` — environment and dependency self-check."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import keyring
import typer

from sybl.config import ConfigError, ConfigManager, config_dir, state_dir
from sybl.secrets import get_provider_key


class CheckStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    detail: str
    remediation: str | None = None


def register(app: typer.Typer) -> None:
    @app.command("doctor")
    def doctor_command(
        live: bool = typer.Option(
            False,
            "--live",
            help="Run network, mic, and inject probes (slower; needs keys/mic).",
        ),
    ) -> None:
        """Run environment and dependency checks."""
        results = run_checks(live=live)
        has_failure = False

        for result in results:
            typer.echo(f"[{result.status.value}] {result.name}: {result.detail}")
            if result.remediation:
                typer.echo(f"  -> {result.remediation}")
            if result.status == CheckStatus.FAIL:
                has_failure = True

        if has_failure:
            raise typer.Exit(code=1)


def run_checks(*, live: bool = False) -> list[CheckResult]:
    results: list[CheckResult] = []

    results.append(
        CheckResult(
            "Python version",
            CheckStatus.PASS,
            (
                f"{sys.version_info.major}."
                f"{sys.version_info.minor}."
                f"{sys.version_info.micro}"
            ),
        )
    )

    for package in (
        "typer",
        "pydantic",
        "keyring",
        "platformdirs",
        "sounddevice",
        "pynput",
    ):
        try:
            importlib.import_module(package)
            results.append(
                CheckResult(
                    f"Import {package}",
                    CheckStatus.PASS,
                    "ok",
                )
            )
        except ImportError as exc:
            results.append(
                CheckResult(
                    f"Import {package}",
                    CheckStatus.FAIL,
                    str(exc),
                )
            )

    results.append(_check_directory_writable("Config directory", config_dir()))
    results.append(_check_directory_writable("State directory", state_dir()))

    try:
        backend = keyring.get_keyring()
        results.append(
            CheckResult(
                "Keyring backend",
                CheckStatus.PASS,
                backend.__class__.__name__,
            )
        )
    except Exception as exc:
        results.append(
            CheckResult(
                "Keyring backend",
                CheckStatus.FAIL,
                str(exc),
            )
        )

    manager = ConfigManager()
    try:
        config = manager.load()
        if manager.path.exists():
            detail = f"valid ({manager.path})"
        else:
            detail = (
                "using defaults (config file not created yet — run `sybl config init`)"
            )
        results.append(
            CheckResult(
                "Configuration",
                CheckStatus.PASS,
                detail,
            )
        )
    except ConfigError as exc:
        results.append(
            CheckResult(
                "Configuration",
                CheckStatus.FAIL,
                str(exc),
            )
        )
        config = None

    if config is not None:
        preferred = config.provider.preferred
        if get_provider_key(preferred):
            results.append(
                CheckResult(
                    "Preferred provider key",
                    CheckStatus.PASS,
                    f"{preferred} key found in keyring",
                )
            )
        else:
            results.append(
                CheckResult(
                    "Preferred provider key",
                    CheckStatus.WARN,
                    (
                        f"No key for preferred provider {preferred!r} — "
                        f"run `sybl config set-key {preferred}`"
                    ),
                )
            )

        results.extend(_check_providers(config))
        results.extend(_check_hotkeys(config))
        results.extend(_check_inject(config))
        results.extend(_check_postprocess(config))
        results.extend(_check_vocabulary(config))
        results.extend(_check_voice_commands(config))
        results.extend(_check_indicator(config))

    results.extend(_check_daemon())
    results.extend(_check_audio())

    if live:
        results.extend(_run_live_checks(config))

    return results


async def _ping_daemon_async() -> CheckResult:
    from sybl.ipc.client import IpcClient, is_daemon_running, load_daemon_info

    if not is_daemon_running():
        return CheckResult(
            "Daemon IPC ping (live)",
            CheckStatus.WARN,
            "Daemon not running",
            "Run: sybl start",
        )
    try:
        client = IpcClient(load_daemon_info())
        await client.ping()
    except Exception as exc:
        return CheckResult(
            "Daemon IPC ping (live)",
            CheckStatus.FAIL,
            str(exc),
            "Restart the daemon: sybl stop && sybl start",
        )
    return CheckResult(
        "Daemon IPC ping (live)",
        CheckStatus.PASS,
        "pong",
    )


def _run_live_checks(config) -> list[CheckResult]:
    import asyncio

    results: list[CheckResult] = []
    results.append(asyncio.run(_ping_daemon_async()))
    if config is not None:
        results.extend(_check_provider_reachability(config))
        results.extend(_check_mic_smoke())
        results.extend(_check_inject_live(config))
    return results


def _check_provider_reachability(config) -> list[CheckResult]:
    import urllib.error
    import urllib.request

    results: list[CheckResult] = []
    preferred = config.provider.preferred
    key = get_provider_key(preferred)
    if not key:
        return [
            CheckResult(
                f"Provider reachability ({preferred})",
                CheckStatus.WARN,
                "No API key configured — skipping probe",
                f"Run: sybl config set-key {preferred}",
            )
        ]

    urls = {
        "groq": "https://api.groq.com/openai/v1/models",
        "deepgram": "https://api.deepgram.com/v1/projects",
    }
    url = urls.get(preferred)
    if url is None:
        return []

    request = urllib.request.Request(url, method="GET")
    if preferred == "groq":
        request.add_header("Authorization", f"Bearer {key}")
    elif preferred == "deepgram":
        request.add_header("Authorization", f"Token {key}")

    try:
        with urllib.request.urlopen(request, timeout=8.0) as response:
            if 200 <= response.status < 300:
                status = CheckStatus.PASS
                detail = f"HTTP {response.status}"
                remediation = None
            elif response.status == 401:
                status = CheckStatus.FAIL
                detail = "HTTP 401 unauthorized"
                remediation = f"Run: sybl config set-key {preferred}"
            else:
                status = CheckStatus.WARN
                detail = f"HTTP {response.status}"
                remediation = None
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            status = CheckStatus.FAIL
            detail = "HTTP 401 unauthorized"
            remediation = f"Run: sybl config set-key {preferred}"
        else:
            status = CheckStatus.WARN
            detail = f"HTTP {exc.code}"
            remediation = None
    except Exception as exc:
        status = CheckStatus.WARN
        detail = f"Request failed: {exc}"
        remediation = "Check network connectivity"

    results.append(
        CheckResult(
            f"Provider reachability ({preferred})",
            status,
            detail,
            remediation,
        )
    )
    return results


def _check_mic_smoke() -> list[CheckResult]:
    try:
        import numpy as np
        import sounddevice as sd
    except ImportError as exc:
        return [
            CheckResult(
                "Mic capture smoke (live)",
                CheckStatus.WARN,
                str(exc),
            )
        ]

    duration = 0.25
    sample_rate = 16000
    try:
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
        rms = float(np.sqrt(np.mean(recording.astype(np.float32) ** 2)))
    except Exception as exc:
        return [
            CheckResult(
                "Mic capture smoke (live)",
                CheckStatus.WARN,
                f"Could not record: {exc}",
                "Check microphone permissions in Windows Settings",
            )
        ]

    if rms < 1.0:
        return [
            CheckResult(
                "Mic capture smoke (live)",
                CheckStatus.WARN,
                f"Very low signal (RMS={rms:.1f}) — silent or muted?",
                "Speak during the probe or check default input device",
            )
        ]
    return [
        CheckResult(
            "Mic capture smoke (live)",
            CheckStatus.PASS,
            f"Captured audio (RMS={rms:.1f})",
        )
    ]


def _check_inject_live(config) -> list[CheckResult]:
    import sys

    if sys.platform != "win32":
        return [
            CheckResult(
                "Inject self-test (live)",
                CheckStatus.WARN,
                "Windows-only clipboard probe skipped",
            )
        ]
    if not config.inject.enabled:
        return [
            CheckResult(
                "Inject self-test (live)",
                CheckStatus.WARN,
                "Injection disabled in config",
                "Enable inject.enabled in config.toml",
            )
        ]
    try:
        import ctypes

        user32 = ctypes.windll.user32
        if not user32.OpenClipboard(None):
            return [
                CheckResult(
                    "Inject self-test (live)",
                    CheckStatus.WARN,
                    "Clipboard busy — close apps holding the clipboard",
                )
            ]
        try:
            user32.EmptyClipboard()
            user32.CloseClipboard()
        except Exception:
            user32.CloseClipboard()
            raise
    except Exception as exc:
        return [
            CheckResult(
                "Inject self-test (live)",
                CheckStatus.WARN,
                f"Clipboard access failed: {exc}",
            )
        ]
    return [
        CheckResult(
            "Inject self-test (live)",
            CheckStatus.PASS,
            "Clipboard read/write available for paste injection",
        )
    ]


def _check_daemon() -> list[CheckResult]:
    from sybl.ipc.client import is_daemon_running, load_daemon_info

    info = load_daemon_info()
    if info is None:
        return [
            CheckResult(
                "Daemon IPC",
                CheckStatus.WARN,
                "Daemon not running (start with `sybl start`)",
            )
        ]
    if not is_daemon_running():
        return [
            CheckResult(
                "Daemon IPC",
                CheckStatus.WARN,
                f"Stale daemon.json (pid={info.pid} not running)",
            )
        ]
    return [
        CheckResult(
            "Daemon IPC",
            CheckStatus.PASS,
            (
                f"Running pid={info.pid} "
                f"command={info.command_port} events={info.event_port}"
            ),
        )
    ]


def _check_providers(_config) -> list[CheckResult]:
    from sybl.providers import all_capabilities, list_providers

    results: list[CheckResult] = []
    registered = set(list_providers())
    for caps in all_capabilities():
        if caps.name not in registered:
            continue
        key_status = "key ok" if get_provider_key(caps.name) else "no key"
        streaming = "stream" if caps.streaming else "batch"
        partials = "partials" if caps.partial_results else "final-only"
        results.append(
            CheckResult(
                f"Provider {caps.name}",
                CheckStatus.PASS if get_provider_key(caps.name) else CheckStatus.WARN,
                f"{streaming}, {partials}, {key_status}",
            )
        )
    return results


def _check_hotkeys(config) -> list[CheckResult]:
    import sys

    from sybl.hotkeys.bindings import BindingParseError, parse_binding

    results: list[CheckResult] = []

    if sys.platform != "win32":
        results.append(
            CheckResult(
                "Global hotkeys",
                CheckStatus.WARN,
                "Windows-only in Phase 4",
            )
        )

    try:
        binding = parse_binding(config.hotkey.binding)
        results.append(
            CheckResult(
                "Hotkey binding",
                CheckStatus.PASS,
                f"{config.hotkey.binding} -> {', '.join(binding.tokens)}",
            )
        )
    except BindingParseError as exc:
        results.append(
            CheckResult(
                "Hotkey binding",
                CheckStatus.FAIL,
                str(exc),
            )
        )

    try:
        cancel = parse_binding(config.hotkey.cancel_binding)
        results.append(
            CheckResult(
                "Cancel binding",
                CheckStatus.PASS,
                f"{config.hotkey.cancel_binding} -> {', '.join(cancel.tokens)}",
            )
        )
    except BindingParseError as exc:
        results.append(
            CheckResult(
                "Cancel binding",
                CheckStatus.FAIL,
                str(exc),
            )
        )

    return results


def _check_inject(config) -> list[CheckResult]:
    import sys

    results: list[CheckResult] = []

    if sys.platform != "win32":
        results.append(
            CheckResult(
                "Text injection",
                CheckStatus.WARN,
                "Windows-only in Phase 5",
            )
        )
        return results

    if not config.inject.enabled:
        results.append(
            CheckResult(
                "Text injection",
                CheckStatus.WARN,
                "disabled in config (transcripts logged only)",
            )
        )
        return results

    try:
        from sybl.inject import create_injector

        create_injector(config)
        results.append(
            CheckResult(
                "Text injection",
                CheckStatus.PASS,
                f"strategy={config.inject.strategy}, clipboard restore enabled",
            )
        )
    except NotImplementedError as exc:
        results.append(
            CheckResult(
                "Text injection",
                CheckStatus.FAIL,
                str(exc),
            )
        )

    return results


def _check_postprocess(config) -> list[CheckResult]:
    from sybl.core.postprocess import process_text

    if not config.postprocess.enabled:
        return [
            CheckResult(
                "Post-processing",
                CheckStatus.WARN,
                "disabled in config (raw provider text used)",
            )
        ]

    sample = process_text(config.postprocess, "  um hello world  ")
    enabled = []
    if config.postprocess.trim_fillers:
        enabled.append("fillers")
    if config.postprocess.collapse_repeated_words:
        enabled.append("repeat-words")
    if config.postprocess.normalize_quotes:
        enabled.append("quotes")
    if config.postprocess.trim_space_before_punctuation:
        enabled.append("punct-space")
    if config.postprocess.capitalize:
        enabled.append("capitalize")
    if config.postprocess.ensure_punctuation:
        enabled.append("punctuation")
    flags = ", ".join(enabled) if enabled else "whitespace only"
    return [
        CheckResult(
            "Post-processing",
            CheckStatus.PASS,
            f"{flags}; sample -> {sample!r}",
        )
    ]


def _check_vocabulary(config) -> list[CheckResult]:
    from sybl.config.vocabulary import VocabularyError, VocabularyStore

    if not config.vocabulary.enabled:
        return [
            CheckResult(
                "Vocabulary hints",
                CheckStatus.WARN,
                "disabled in config (no STT hint terms sent)",
            )
        ]

    store = VocabularyStore()
    try:
        terms = store.load_terms()
    except VocabularyError as exc:
        return [
            CheckResult(
                "Vocabulary hints",
                CheckStatus.FAIL,
                str(exc),
            )
        ]

    if not terms:
        return [
            CheckResult(
                "Vocabulary hints",
                CheckStatus.WARN,
                f"enabled but empty ({store.path})",
            )
        ]

    preview = ", ".join(terms[:5])
    suffix = f" (+{len(terms) - 5} more)" if len(terms) > 5 else ""
    return [
        CheckResult(
            "Vocabulary hints",
            CheckStatus.PASS,
            f"{len(terms)} term(s): {preview}{suffix}",
        )
    ]


def _check_voice_commands(config) -> list[CheckResult]:
    if not config.voice_commands.enabled:
        return [
            CheckResult(
                "Voice commands",
                CheckStatus.WARN,
                "disabled in config",
            )
        ]
    return [
        CheckResult(
            "Voice commands",
            CheckStatus.PASS,
            "new line, period, comma; Esc cancels before inject",
        )
    ]


def _check_indicator(config) -> list[CheckResult]:
    indicator = config.indicator
    if not indicator.enabled or indicator.strategy == "none":
        return [
            CheckResult(
                "Capture indicator",
                CheckStatus.WARN,
                "disabled in config (no on-screen listening cue)",
            )
        ]

    sound_note = ""
    if indicator.sound_enabled:
        sound_note = "; sound cue enabled"

    if sys.platform != "win32":
        return [
            CheckResult(
                "Capture indicator",
                CheckStatus.WARN,
                f"overlay strategy not implemented on {sys.platform} yet{sound_note}",
            )
        ]

    try:
        import tkinter as tk

        root = tk.Tk()
        root.withdraw()
        root.destroy()
    except Exception as exc:
        return [
            CheckResult(
                "Capture indicator",
                CheckStatus.FAIL,
                f"tkinter unavailable: {exc}",
            )
        ]

    return [
        CheckResult(
            "Capture indicator",
            CheckStatus.PASS,
            f"overlay enabled ({indicator.size_px}px pill near cursor){sound_note}",
        )
    ]


def _check_audio() -> list[CheckResult]:
    results: list[CheckResult] = []
    try:
        import sounddevice as sd

        from sybl.audio.devices import list_input_devices
    except ImportError as exc:
        results.append(
            CheckResult(
                "Import sounddevice",
                CheckStatus.FAIL,
                str(exc),
            )
        )
        return results

    devices = list_input_devices()
    if devices:
        default = next((d for d in devices if d.is_default), devices[0])
        results.append(
            CheckResult(
                "Input devices",
                CheckStatus.PASS,
                f"{len(devices)} found (default: {default.name})",
            )
        )
    else:
        results.append(
            CheckResult(
                "Input devices",
                CheckStatus.WARN,
                "No input devices found — check microphone permissions",
            )
        )
        return results

    try:
        sd.check_input_settings(device=sd.default.device[0], channels=1)
        results.append(
            CheckResult(
                "Default input probe",
                CheckStatus.PASS,
                "default input settings OK",
            )
        )
    except Exception as exc:
        results.append(
            CheckResult(
                "Default input probe",
                CheckStatus.WARN,
                f"Could not open default input — check mic permissions: {exc}",
            )
        )

    return results


def _check_directory_writable(name: str, path: Path) -> CheckResult:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".sybl_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return CheckResult(name, CheckStatus.PASS, str(path))
    except OSError as exc:
        return CheckResult(name, CheckStatus.FAIL, f"{path}: {exc}")
