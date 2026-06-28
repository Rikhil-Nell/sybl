# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-26

First public release. Navi is a BYOK voice dictation daemon with global
push-to-talk, STT provider plugins, clipboard-paste injection, and a Textual TUI.

### Added

- CLI: `start`, `stop`, `status`, `tui`, `config`, `doctor`, `audio`, `transcribe`, `hotkey`
- Config system (TOML + Pydantic) and OS keyring secret storage
- Audio capture pipeline (16 kHz mono PCM, resampling, RMS metering, debug WAV)
- STT providers: Groq Whisper (batch) and Deepgram (streaming + batch)
- Global PTT hotkeys on Windows (`pynput`) with focus capture at activation
- Clipboard-paste text injection on Windows with clipboard restore
- Rule-based post-processing pipeline (fillers, capitalization, punctuation cleanup)
- Daemon + TCP NDJSON IPC; Textual TUI (logs, status, history, settings, onboarding)
- Windows listening indicator (tkinter overlay pill near cursor)
- Custom vocabulary STT hints (`navi config vocab`) for Deepgram keyterms and Groq prompt
- Voice commands in final transcripts: `new line`, `period`, `comma`
- Duplicate punctuation collapse in post-processing

### Changed

- Removed `scratch that` voice command; use **Esc** while holding the hotkey to cancel
  before injection instead

### Notes

- **Windows-first:** hotkeys, injection, and the listening indicator are proven on
  Windows. macOS/Linux backends are stubs behind interfaces.
- Integration tests requiring a microphone or live API keys are marked `@integration`
  and excluded from CI.

[0.1.0]: https://github.com/Rikhil-Nell/navi/releases/tag/v0.1.0
