"""Tests for vocabulary storage and STT hint helpers."""

from pathlib import Path

import pytest

from navi.config.vocabulary import (
    VocabularyError,
    VocabularyStore,
    build_groq_vocabulary_prompt,
)


def test_add_list_remove_terms(tmp_path: Path) -> None:
    path = tmp_path / "vocabulary.toml"
    store = VocabularyStore(path)
    assert store.load_terms() == []

    store.add_term("Rikhil")
    store.add_term("Navi")
    assert store.load_terms() == ["Rikhil", "Navi"]

    store.add_term("rikhil")
    assert store.load_terms() == ["Rikhil", "Navi"]

    store.remove_term("Navi")
    assert store.load_terms() == ["Rikhil"]


def test_add_empty_term_raises(tmp_path: Path) -> None:
    store = VocabularyStore(tmp_path / "vocabulary.toml")
    with pytest.raises(VocabularyError, match="empty"):
        store.add_term("   ")


def test_build_groq_vocabulary_prompt() -> None:
    prompt = build_groq_vocabulary_prompt(["Rikhil", "Navi"])
    assert "Rikhil" in prompt
    assert "Navi" in prompt
