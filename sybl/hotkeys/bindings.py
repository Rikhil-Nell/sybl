"""Parse and validate hotkey binding strings."""

from __future__ import annotations

from dataclasses import dataclass

_MODIFIER_ALIASES: dict[str, str] = {
    "ctrl": "ctrl",
    "control": "ctrl",
    "shift": "shift",
    "alt": "alt",
    "option": "alt",
    "cmd": "cmd",
    "win": "cmd",
    "super": "cmd",
    "meta": "cmd",
}

_SPECIAL_KEYS: dict[str, str] = {
    "space": "space",
    "spc": "space",
    "enter": "enter",
    "return": "enter",
    "tab": "tab",
    "esc": "esc",
    "escape": "esc",
    "backspace": "backspace",
    "delete": "delete",
    "del": "delete",
    "insert": "insert",
    "home": "home",
    "end": "end",
    "pageup": "pageup",
    "pagedown": "pagedown",
    "up": "up",
    "down": "down",
    "left": "left",
    "right": "right",
    "f1": "f1",
    "f2": "f2",
    "f3": "f3",
    "f4": "f4",
    "f5": "f5",
    "f6": "f6",
    "f7": "f7",
    "f8": "f8",
    "f9": "f9",
    "f10": "f10",
    "f11": "f11",
    "f12": "f12",
}


class BindingParseError(ValueError):
    """Raised when a binding string cannot be parsed."""


@dataclass(frozen=True)
class ParsedBinding:
    """Normalized binding tokens in lowercase semantic form."""

    tokens: tuple[str, ...]

    @property
    def token_set(self) -> frozenset[str]:
        return frozenset(self.tokens)


def parse_binding(binding: str) -> ParsedBinding:
    """Parse a binding like ``ctrl+shift+space`` into normalized tokens."""
    raw = binding.strip()
    if not raw:
        raise BindingParseError("Binding cannot be empty")

    parts = [part.strip().lower() for part in raw.split("+") if part.strip()]
    if not parts:
        raise BindingParseError("Binding cannot be empty")

    normalized: list[str] = []
    for part in parts:
        if part in _MODIFIER_ALIASES:
            normalized.append(_MODIFIER_ALIASES[part])
            continue
        if part in _SPECIAL_KEYS:
            normalized.append(_SPECIAL_KEYS[part])
            continue
        if len(part) == 1 and part.isprintable():
            normalized.append(part)
            continue
        raise BindingParseError(f"Unknown binding token: {part!r}")

    if len(normalized) != len(set(normalized)):
        raise BindingParseError(f"Duplicate keys in binding: {binding!r}")

    return ParsedBinding(tokens=tuple(sorted(normalized)))
