"""Tests for transcript history ring buffer."""

from __future__ import annotations

from sybl.core.history import TranscriptHistory


def test_history_capacity() -> None:
    history = TranscriptHistory(capacity=2)
    history.add(
        raw_text="a",
        final_text="A",
        provider="groq",
        model="m",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
    )
    history.add(
        raw_text="b",
        final_text="B",
        provider="groq",
        model="m",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
    )
    history.add(
        raw_text="c",
        final_text="C",
        provider="groq",
        model="m",
        audio_duration_seconds=1.0,
        latency_seconds=0.5,
    )
    entries = history.get_recent()
    assert len(entries) == 2
    assert entries[0].final_text == "B"
    assert entries[1].final_text == "C"
