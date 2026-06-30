"""Shared questionary helpers for CLI wizards."""

from __future__ import annotations

import questionary
from questionary import Style

from sybl.secrets import PROVIDER_KEYS

_WIZARD_STYLE = Style(
    [
        ("qmark", "fg:cyan bold"),
        ("question", "bold"),
        ("answer", "fg:cyan"),
        ("pointer", "fg:cyan bold"),
        ("highlighted", "fg:cyan bold"),
        ("selected", "fg:cyan"),
    ]
)


def pick_provider(*, message: str = "Choose your STT provider") -> str | None:
    choice = questionary.select(
        message,
        choices=list(PROVIDER_KEYS),
        style=_WIZARD_STYLE,
    ).ask()
    if choice is None:
        return None
    return str(choice)


def prompt_api_key(provider: str) -> str | None:
    return questionary.password(
        f"Enter API key for {provider}",
        validate=lambda text: bool(text.strip()) or "API key is required",
        style=_WIZARD_STYLE,
    ).ask()


def pick_hotkey_mode() -> str | None:
    choice = questionary.select(
        "Hotkey interaction mode",
        choices=[
            questionary.Choice("Both — hold for PTT, double-press for toggle", "both"),
            questionary.Choice("Push-to-talk only", "ptt"),
            questionary.Choice("Toggle only", "toggle"),
        ],
        style=_WIZARD_STYLE,
    ).ask()
    if choice is None:
        return None
    return str(choice)


def confirm_mic_smoke() -> bool:
    answer = questionary.confirm(
        "Run a quick microphone smoke test?",
        default=True,
        style=_WIZARD_STYLE,
    ).ask()
    return bool(answer)
