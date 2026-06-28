"""Tests for vocabulary storage and STT hint helpers."""

from pathlib import Path

import pytest

from sybl.config.vocabulary import (
    VocabularyError,
    VocabularyStore,
    build_groq_vocabulary_prompt,
)


def test_add_list_remove_terms(tmp_path: Path) -> None:
    path = tmp_path / "vocabulary.toml"
    store = VocabularyStore(path)
    assert store.load_terms() == []

    store.add_term("Rikhil")
    store.add_term("sybl")
    assert store.load_terms() == ["Rikhil", "sybl"]

    store.add_term("rikhil")
    assert store.load_terms() == ["Rikhil", "sybl"]

    store.remove_term("sybl")
    assert store.load_terms() == ["Rikhil"]


def test_add_empty_term_raises(tmp_path: Path) -> None:
    store = VocabularyStore(tmp_path / "vocabulary.toml")
    with pytest.raises(VocabularyError, match="empty"):
        store.add_term("   ")


def test_build_groq_vocabulary_prompt() -> None:
    prompt = build_groq_vocabulary_prompt(["Rikhil", "sybl"])
    assert "Rikhil" in prompt
    assert "sybl" in prompt
