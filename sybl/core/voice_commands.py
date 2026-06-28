"""Parse spoken voice commands from final transcripts."""

from __future__ import annotations

import re

from sybl.config.models import VoiceCommandsConfig
from sybl.core.postprocess import collapse_duplicate_punctuation

_NEWLINE_PHRASES = ("new line", "newline")
_PUNCTUATION_PHRASES = {
    "period": ".",
    "comma": ",",
}


def apply_voice_commands(config: VoiceCommandsConfig, text: str) -> str:
    if not config.enabled or not text.strip():
        return text

    result = text.strip()
    for phrase in _NEWLINE_PHRASES:
        result = _replace_phrase(result, phrase, "\n")
    for phrase, symbol in _PUNCTUATION_PHRASES.items():
        result = _replace_punctuation_phrase(result, phrase, symbol)
    result = re.sub(r"[ \t]+\n", "\n", result)
    result = re.sub(r"\n[ \t]+", "\n", result)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return collapse_duplicate_punctuation(result).strip()


def _replace_punctuation_phrase(text: str, phrase: str, symbol: str) -> str:
    """Replace spoken punctuation unless that symbol is already present."""
    pattern = re.compile(
        rf"\b{re.escape(phrase)}\b(?!\s*{re.escape(symbol)})",
        re.IGNORECASE,
    )
    return pattern.sub(symbol, text)


def _replace_phrase(text: str, phrase: str, replacement: str) -> str:
    pattern = re.compile(rf"\b{re.escape(phrase)}\b", re.IGNORECASE)
    return pattern.sub(replacement, text)
