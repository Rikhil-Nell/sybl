"""User vocabulary terms passed to STT providers as hints."""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path

import tomli_w

from sybl.config.paths import vocabulary_path

logger = logging.getLogger("sybl.config.vocabulary")


class VocabularyError(Exception):
    """Raised when vocabulary cannot be loaded or saved."""


class VocabularyStore:
    """Load and persist STT hint terms in the state directory."""

    def __init__(self, path: Path | None = None) -> None:
        self._path = path or vocabulary_path()

    @property
    def path(self) -> Path:
        return self._path

    def load_terms(self) -> list[str]:
        if not self._path.exists():
            return []
        try:
            with self._path.open("rb") as handle:
                data = tomllib.load(handle)
        except tomllib.TOMLDecodeError as exc:
            raise VocabularyError(f"Invalid TOML in {self._path}: {exc}") from exc

        raw = data.get("terms", [])
        if not isinstance(raw, list):
            raise VocabularyError(f"'terms' must be a list in {self._path}")

        terms: list[str] = []
        seen: set[str] = set()
        for item in raw:
            if not isinstance(item, str):
                continue
            term = item.strip()
            if not term:
                continue
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            terms.append(term)
        return terms

    def save_terms(self, terms: list[str]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"terms": terms}
        with self._path.open("wb") as handle:
            tomli_w.dump(payload, handle)

    def add_term(self, term: str) -> list[str]:
        cleaned = term.strip()
        if not cleaned:
            raise VocabularyError("Term cannot be empty")
        terms = self.load_terms()
        if any(existing.casefold() == cleaned.casefold() for existing in terms):
            return terms
        terms.append(cleaned)
        self.save_terms(terms)
        logger.info("Added vocabulary term: %s", cleaned)
        return terms

    def remove_term(self, term: str) -> list[str]:
        cleaned = term.strip()
        terms = [
            existing
            for existing in self.load_terms()
            if existing.casefold() != cleaned.casefold()
        ]
        self.save_terms(terms)
        return terms


def build_groq_vocabulary_prompt(terms: list[str]) -> str:
    """Build a Whisper initial prompt from user vocabulary terms."""
    return "Common terms: " + ", ".join(terms)


def format_deepgram_keyterms(terms: list[str]) -> list[str]:
    """Return keyterms for Deepgram nova models."""
    return terms
