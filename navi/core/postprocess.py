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
    if config.collapse_repeated_words:
        passes.append(collapse_repeated_words)
    if config.normalize_quotes:
        passes.append(normalize_quotes)
    if config.trim_space_before_punctuation:
        passes.append(trim_space_before_punctuation)
    if config.collapse_duplicate_punctuation:
        passes.append(collapse_duplicate_punctuation)
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


def collapse_repeated_words(text: str) -> str:
    return re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", text, flags=re.IGNORECASE)


def normalize_quotes(text: str) -> str:
    replacements = {
        "\u201c": '"',
        "\u201d": '"',
        "\u2018": "'",
        "\u2019": "'",
        "\u2014": "-",
        "\u2013": "-",
    }
    result = text
    for source, target in replacements.items():
        result = result.replace(source, target)
    return result


def trim_space_before_punctuation(text: str) -> str:
    return re.sub(r"\s+([,.!?;:])", r"\1", text)


def collapse_duplicate_punctuation(text: str) -> str:
    """Collapse doubled punctuation like ',,' or '..'."""
    result = re.sub(r"([,.!?;:])\1+", r"\1", text)
    result = re.sub(r"\s+([,.!?;:])", r"\1", result)
    result = re.sub(r"([,.!?;:])\s+([,.!?;:])", r"\1", result)
    return result


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
