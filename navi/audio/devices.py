"""Input device discovery and resolution."""

from __future__ import annotations

import re
import sys

import sounddevice as sd

from navi.audio.errors import DeviceNotFoundError
from navi.audio.types import TARGET_SAMPLE_RATE, DeviceInfo


def _normalize_device_name(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _hostapi_rank(hostapi_index: int) -> int:
    hostapis = sd.query_hostapis()
    api_name = str(hostapis[hostapi_index]["name"]).lower()
    if sys.platform == "win32":
        for rank, key in enumerate(("wasapi", "wdm", "directsound", "mme")):
            if key in api_name:
                return rank
        return 99
    if sys.platform == "darwin":
        return 0 if "core" in api_name else 1
    return 0 if "alsa" in api_name or "jack" in api_name else 1


def _can_open_input(device_index: int, samplerate: float) -> bool:
    for rate in (int(samplerate), TARGET_SAMPLE_RATE, 44100, 48000):
        try:
            sd.check_input_settings(device=device_index, channels=1, samplerate=rate)
            return True
        except Exception:
            continue
    try:
        sd.check_input_settings(device=device_index, channels=1)
        return True
    except Exception:
        return False


def _dedupe_devices(devices: list[DeviceInfo]) -> list[DeviceInfo]:
    best_by_name: dict[str, DeviceInfo] = {}
    rank_by_name: dict[str, tuple[int, int, int]] = {}

    for device in devices:
        key = _normalize_device_name(device.name)
        hostapi = sd.query_devices(device.index)["hostapi"]
        rank = (
            0 if device.is_default else 1,
            _hostapi_rank(int(hostapi)),
            device.index,
        )
        existing = rank_by_name.get(key)
        if existing is None or rank < existing:
            best_by_name[key] = device
            rank_by_name[key] = rank

    return sorted(best_by_name.values(), key=lambda d: (not d.is_default, d.index))


def _wasapi_hostapi_index() -> int | None:
    if sys.platform != "win32":
        return None
    for index, hostapi in enumerate(sd.query_hostapis()):
        if "wasapi" in str(hostapi["name"]).lower():
            return index
    return None


def _is_likely_microphone(name: str) -> bool:
    lowered = name.lower()
    excluded = (
        "stereo mix",
        "loopback",
        "wave out mix",
        "what u hear",
        "pc speaker",
        "sound mapper",
        "primary sound capture driver",
        "mapper - output",
        "input ()",
    )
    if any(token in lowered for token in excluded):
        return False
    if lowered.endswith(" output") or lowered.endswith(" output)"):
        return False
    return True


def list_input_devices(*, available_only: bool = True) -> list[DeviceInfo]:
    """Return input-capable audio devices, optionally filtered to openable mics."""
    default_input = sd.default.device[0]
    wasapi_index = _wasapi_hostapi_index()
    devices: list[DeviceInfo] = []

    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] <= 0:
            continue
        if wasapi_index is not None and int(device["hostapi"]) != wasapi_index:
            continue
        name = str(device["name"])
        if available_only and not _is_likely_microphone(name):
            continue
        devices.append(
            DeviceInfo(
                index=index,
                name=name,
                default_samplerate=float(device["default_samplerate"]),
                max_input_channels=int(device["max_input_channels"]),
                is_default=index == default_input,
            )
        )

    if available_only:
        devices = [
            device
            for device in devices
            if _can_open_input(device.index, device.default_samplerate)
        ]
        devices = _dedupe_devices(devices)
        devices = _mark_default_device(devices, default_input)

    return devices


def _mark_default_device(
    devices: list[DeviceInfo],
    default_input: int | None,
) -> list[DeviceInfo]:
    if not devices:
        return devices
    if any(device.is_default for device in devices):
        return devices

    default_name = ""
    if default_input is not None and default_input >= 0:
        default_name = _normalize_device_name(get_device_name(int(default_input)))

    marked: list[DeviceInfo] = []
    best_index: int | None = None
    for device in devices:
        name = _normalize_device_name(device.name)
        if default_name and (
            name == default_name or default_name in name or name in default_name
        ):
            best_index = device.index
            break

    if best_index is None:
        best_index = devices[0].index

    for device in devices:
        marked.append(
            DeviceInfo(
                index=device.index,
                name=device.name,
                default_samplerate=device.default_samplerate,
                max_input_channels=device.max_input_channels,
                is_default=device.index == best_index,
            )
        )
    return marked


def _format_device_list(devices: list[DeviceInfo]) -> str:
    if not devices:
        return "(no input devices found)"
    lines = [f"  [{d.index}] {d.name}" for d in devices]
    return "\n".join(lines)


def resolve_device(spec: str | None) -> int:
    """Resolve a device spec (None, index, or name substring) to a device index."""
    devices = list_input_devices()

    if spec is None or spec.strip() == "":
        default_index = sd.default.device[0]
        available_indices = {d.index for d in devices}
        if default_index in available_indices:
            return int(default_index)
        if devices:
            default_device = next((d for d in devices if d.is_default), devices[0])
            return default_device.index
        raise DeviceNotFoundError(
            "No usable input device found.\n"
            f"Available devices:\n{_format_device_list(devices)}"
        )

    spec_stripped = spec.strip()

    if spec_stripped.isdigit():
        index = int(spec_stripped)
        device_indices = {d.index for d in devices}
        if index not in device_indices:
            raise DeviceNotFoundError(
                f"Device index {index} not found.\n"
                f"Available devices:\n{_format_device_list(devices)}"
            )
        return index

    spec_lower = spec_stripped.lower()
    matches = [d for d in devices if spec_lower in d.name.lower()]
    if not matches:
        raise DeviceNotFoundError(
            f"No input device matching {spec_stripped!r}.\n"
            f"Available devices:\n{_format_device_list(devices)}"
        )

    exact = [d for d in matches if d.name.lower() == spec_lower]
    if exact:
        return exact[0].index

    matches.sort(key=lambda d: len(d.name))
    return matches[0].index


def get_device_name(device_index: int) -> str:
    """Return the human-readable name for a device index."""
    device = sd.query_devices(device_index)
    return str(device["name"])
