"""`navi doctor` — environment and dependency self-check."""

from __future__ import annotations

import importlib
import sys
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

import keyring
import typer

from navi.config import ConfigError, ConfigManager, config_dir, state_dir
from navi.secrets import get_provider_key


class CheckStatus(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: CheckStatus
    detail: str


def register(app: typer.Typer) -> None:
    @app.command("doctor")
    def doctor_command() -> None:
        """Run environment and dependency checks."""
        results = run_checks()
        has_failure = False

        for result in results:
            typer.echo(f"[{result.status.value}] {result.name}: {result.detail}")
            if result.status == CheckStatus.FAIL:
                has_failure = True

        if has_failure:
            raise typer.Exit(code=1)


def run_checks() -> list[CheckResult]:
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
                "using defaults (config file not created yet — run `navi config init`)"
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
                        f"run `navi config set-key {preferred}`"
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

    return results


def _check_daemon() -> list[CheckResult]:
    from navi.ipc.client import is_daemon_running, load_daemon_info

    info = load_daemon_info()
    if info is None:
        return [
            CheckResult(
                "Daemon IPC",
                CheckStatus.WARN,
                "Daemon not running (start with `navi start`)",
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
    from navi.providers import all_capabilities, list_providers

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

    from navi.hotkeys.bindings import BindingParseError, parse_binding

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
        from navi.inject import create_injector

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
    from navi.core.postprocess import process_text

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
    from navi.config.vocabulary import VocabularyError, VocabularyStore

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
            "new line, scratch that, period, comma (final transcript)",
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

    if sys.platform != "win32":
        return [
            CheckResult(
                "Capture indicator",
                CheckStatus.WARN,
                f"overlay strategy not implemented on {sys.platform} yet",
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
            f"overlay enabled ({indicator.size_px}px pill near cursor)",
        )
    ]


def _check_audio() -> list[CheckResult]:
    results: list[CheckResult] = []
    try:
        import sounddevice as sd

        from navi.audio.devices import list_input_devices
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
        probe = path / ".navi_write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return CheckResult(name, CheckStatus.PASS, str(path))
    except OSError as exc:
        return CheckResult(name, CheckStatus.FAIL, f"{path}: {exc}")
