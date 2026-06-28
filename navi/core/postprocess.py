"""Rule-based post-processing for provider transcripts."""

from __future__ import annotations

import re
from collections.abc import Callable
from typing import Protocol

from navi.config.models import PostProcessConfig

_FILLER_WORDS = ("um", "uh", "erm", "ah")
_LEADING_FILLERS = re.compile(
    rf"^((?:{'|'.join(_FILLER_WORDS)})[,.]?\s+)+",
    re.IGNORECASE,
)
_TRAILING_FILLERS = re.compile(
    rf"(\s+(?:{'|'.join(_FILLER_WORDS)})[,.]?)+$",
    re.IGNORECASE,
)
_SENTENCE_ENDINGS = frozenset(".!?")


class PostProcessor(Protocol):
    def process(self, text: str) -> str: ...


class PipelineProcessor:
    def __init__(self, passes: list[Callable[[str], str]]) -> None:
        self._passes = passes

    def process(self, text: str) -> str:
        result = text
        for step in self._passes:
            result = step(result)
        return result


def process_text(config: PostProcessConfig, text: str) -> str:
    """Run configured cleanup passes on provider text."""
    if not config.enabled or not text.strip():
        return text
    return build_post_processor(config).process(text)


def build_post_processor(config: PostProcessConfig) -> PostProcessor:
    passes: list[Callable[[str], str]] = [normalize_whitespace]
    if config.trim_fillers:
        passes.append(trim_filler_words)
    if config.capitalize:
        passes.append(capitalize_first)
    if config.ensure_punctuation:
        passes.append(ensure_terminal_punctuation)
    return PipelineProcessor(passes)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def trim_filler_words(text: str) -> str:
    result = text.strip()
    while True:
        updated = _LEADING_FILLERS.sub("", result).strip()
        updated = _TRAILING_FILLERS.sub("", updated).strip()
        if updated == result:
            return result
        result = updated


def capitalize_first(text: str) -> str:
    for index, char in enumerate(text):
        if char.isalpha():
            return text[:index] + char.upper() + text[index + 1 :]
    return text


def ensure_terminal_punctuation(text: str) -> str:
    stripped = text.rstrip()
    if not stripped:
        return text
    if stripped[-1] in _SENTENCE_ENDINGS:
        return text
    if not any(char.isalpha() for char in stripped):
        return text
    return stripped + "."
