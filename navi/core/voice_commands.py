"""Parse spoken voice commands from final transcripts."""

from __future__ import annotations

import re
from dataclasses import dataclass

from navi.config.models import VoiceCommandsConfig

_SCRATCH_PHRASES = ("scratch that", "undo that")
_NEWLINE_PHRASES = ("new line", "newline")
_PUNCTUATION_PHRASES = {
    "period": ".",
    "comma": ",",
}


@dataclass(frozen=True)
class VoiceCommandResult:
    text: str
    skip_inject: bool = False


def apply_voice_commands(config: VoiceCommandsConfig, text: str) -> VoiceCommandResult:
    if not config.enabled or not text.strip():
        return VoiceCommandResult(text=text)

    stripped = text.strip()
    if _is_scratch_command(stripped):
        return VoiceCommandResult(text="", skip_inject=True)

    result = stripped
    for phrase in _NEWLINE_PHRASES:
        result = _replace_phrase(result, phrase, "\n")
    for phrase, symbol in _PUNCTUATION_PHRASES.items():
        result = _replace_phrase(result, phrase, symbol)
    result = re.sub(r"[ \t]+\n", "\n", result)
    result = re.sub(r"\n[ \t]+", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return VoiceCommandResult(text=result.strip())


def _is_scratch_command(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", text.strip().casefold())
    return normalized in _SCRATCH_PHRASES


def _replace_phrase(text: str, phrase: str, replacement: str) -> str:
    pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
    return pattern.sub(replacement, text)
