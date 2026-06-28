# Development

This document covers local development, the phased build history, and testing. For the
living architecture map see [AGENTS.md](../AGENTS.md). For what's next see
[ROADMAP.md](ROADMAP.md).

## Local setup

```powershell
git clone https://github.com/Rikhil-Nell/navi.git
cd navi
uv sync
uv run navi doctor
```

## Commands

```powershell
# Lint + unit tests (CI parity)
uv run ruff check navi tests
uv run pytest -m "not integration" -q

# Run from source
uv run navi start
uv run navi tui

# Integration (manual — mic + API keys)
uv run pytest -m integration
```

## Phase history (condensed)

| Phase | Milestone |
| --- | --- |
| **0** | CLI, Pydantic config, keyring secrets, logging, `doctor` |
| **1** | Audio capture — sounddevice callback → asyncio queue, 16 kHz mono, RMS metering |
| **2** | STT abstraction + Groq Whisper batch |
| **3** | Deepgram streaming WebSocket + provider manager |
| **4** | Global PTT hotkeys (`pynput`), focus capture, dictation loop |
| **5** | Windows clipboard-paste injection |
| **5.5** | Rule-based post-processing pipeline |
| **6** | Daemon + TCP NDJSON IPC |
| **7** | Textual TUI (logs, status, history, settings, onboarding) |
| **8** | Windows tkinter listening indicator |
| **9** | Vocabulary STT hints, voice commands, extended postprocess |
| **10** | OSS release — PyPI, docs hub, CI, contributor templates |

## Architecture notes

- **Daemon is authoritative** — owns mic, providers, state machine, injection, config.
- **TUI is a client** — attaches over IPC; config writes go through the daemon.
- **Platform code behind interfaces** — `HotkeyManager`, `TextInjector`, `CaptureIndicator`.

Deep dives:

- [DAEMON.md](DAEMON.md) — IPC protocol and process model
- [POPUP-SPIKE.md](POPUP-SPIKE.md) — listening indicator research and tk MVP

## Integration tests

Tests marked `@integration` require real hardware or live STT API keys. They are
**excluded from CI** intentionally. Run locally when changing audio, providers, or
end-to-end dictation paths.

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for PR expectations, commit message rules,
and PyPI release maintainer notes.

## Research

Historical planning notes live in [RESEARCH-NOTES.md](RESEARCH-NOTES.md).
