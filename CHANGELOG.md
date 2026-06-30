# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.2] - 2026-06-29

Mission-control TUI overhaul, scriptable CLI, and Qt dock listening pill as the
default Windows indicator.

### Added

- **Mission-control TUI** — Sibyl Royal theme; hero status band with RMS meter;
  live band for streaming partials; session detail pane; transcripts over logs
- **Settings config editor** — section rail, labeled forms, sound-cue rows; all
  writes via daemon IPC
- **`sybl config edit`** and dashboard **`e`** — open `config.toml` in `$EDITOR`,
  reload running daemon
- **Qt dock listening pill** — top-center notch-style overlay with wave bars,
  elapsed timer, and transcribing spinner; multi-monitor DPI-safe positioning
- **Scriptable CLI** — `sybl setup`, `restart`, `logs`, `providers`; `config get`/`set`;
  `--json` on `status`/`doctor`/`config show`; stable exit codes; `--no-input`
- **`sybl indicator demo`** — preview the pill without the daemon
- **`docs/CLI.md`** and **`docs/OVERLAY.md`**

### Changed

- **Qt pill is the default indicator** — PySide6 ships as a core dependency; no
  `[pill]` extra; legacy `overlay`/`orb` config values normalize to `pill`
- Tkinter cursor-following overlay removed from the factory path
- Pill stays visible through processing/injecting; hides on idle/cancel/error

## [0.1.1] - 2026-06-28

Incremental polish release: Wispr-style hotkeys, background daemon, custom sound cues,
TUI settings, and contributor hygiene.

### Added

- **`both` hotkey mode (default)** — PTT (hold) and toggle (double-press) on the same
  binding (`[hotkey] mode`, `ptt_hold_ms`, `toggle_double_press_ms`)
- **Toggle-only mode** — `[hotkey] mode = "toggle"` for hands-free sessions
- **Background daemon** — `sybl start` detaches by default (Windows uses `pythonw`);
  `sybl start --foreground` for debug
- **Custom sound cues** — `sounds/` folder beside `config.toml` (created on
  `sybl config init`); drop or import `start.wav` / `stop.wav`; auto-trim via
  `sound_max_seconds`; built-in chime fallback
- **TUI sound settings** — volume, browse/import WAV, built-in vs custom per cue
- **In-TUI hotkey settings** — binding, mode, cancel key, toggle window
- **`sybl doctor --live`** — optional provider reachability, mic smoke, clipboard probes
- **IPC sound commands** — `list_sounds`, `import_sound`, `clear_sound`
- **`scripts/run_tests.py`** / **`scripts/run_tests.sh`** — hermetic CI-parity test runner
- **Cross-platform CI grep** — flags Unix-only patterns in PR diffs
- **AGENTS.md contribution rubric** — want/don't-want and footprint ladder

### Changed

- **Listening pill** — hidden until dictation starts; follows cursor while listening
- **TUI event stream** — fixed premature disconnects; reconnects quietly
- Dependency upper bounds (`>=floor,<next_major`) on all PyPI packages
- Config validates hotkey binding strings at load time
- `SYBL_CONFIG_DIR` / `SYBL_STATE_DIR` env overrides for tests and isolation
- Default hotkey binding `ctrl+alt+space` (avoids Windows Terminal conflict)

### Fixed

- Toggle/`both` mode crash when `create_hotkey_manager` rejected non-PTT modes
- Blank console window on background start (spawn via `pythonw.exe` on Windows)
- Indicator overlay stuck visible at top-left before first session
- TUI Settings crash when selecting built-in sound cue (Textual Select tuple order)

## [0.1.0] - 2026-06-26

First public release. sybl is a BYOK voice dictation daemon with global
push-to-talk, STT provider plugins, clipboard-paste injection, and a Textual TUI.

### Added

- CLI: `sybl start`, `sybl stop`, `sybl status`, `sybl tui`, `sybl config`, `sybl doctor`, `sybl audio`, `sybl transcribe`, `sybl hotkey`
- Config system (TOML + Pydantic) and OS keyring secret storage
- Audio capture pipeline (16 kHz mono PCM, resampling, RMS metering, debug WAV)
- STT providers: Groq Whisper (batch) and Deepgram (streaming + batch)
- Global PTT hotkeys on Windows (`pynput`) with focus capture at activation
- Clipboard-paste text injection on Windows with clipboard restore
- Rule-based post-processing pipeline (fillers, capitalization, punctuation cleanup)
- Daemon + TCP NDJSON IPC; Textual TUI (logs, status, history, settings, onboarding)
- Windows listening indicator (tkinter overlay pill near cursor)
- Custom vocabulary STT hints (`sybl config vocab`) for Deepgram keyterms and Groq prompt
- Voice commands in final transcripts: `new line`, `period`, `comma`
- Duplicate punctuation collapse in post-processing

### Changed

- **Rebrand:** project renamed from Navi to **sybl** (`sybl` CLI, PyPI package `sybl`)
- Removed `scratch that` voice command; use **Esc** while holding the hotkey to cancel
  before injection instead

### Notes

- **Windows-first:** hotkeys, injection, and the listening indicator are proven on
  Windows. macOS/Linux backends are stubs behind interfaces.
- Integration tests requiring a microphone or live API keys are marked `@integration`
  and excluded from CI.

[0.1.2]: https://github.com/Rikhil-Nell/sybl/releases/tag/v0.1.2
[0.1.1]: https://github.com/Rikhil-Nell/sybl/releases/tag/v0.1.1
[0.1.0]: https://github.com/Rikhil-Nell/sybl/releases/tag/v0.1.0
