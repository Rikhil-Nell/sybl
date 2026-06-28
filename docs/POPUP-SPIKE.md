# Popup / Capture Indicator — Spike Notes

> Phase 8 research. Windows-first decision for sybl MVP.

## Problem

Users need a visible cue that sybl is listening while push-to-talk is held. The TUI
only helps when attached; the popup must work from any focused app.

## Options considered (Windows)

| Approach | Verdict |
|----------|---------|
| **tkinter topmost borderless window** | **Selected for MVP** — stdlib, no new deps, good enough pill + level bar |
| ctypes + user32 layered window | Lightweight but more boilerplate; defer unless tkinter fails |
| pystray / tray icon | Easy but not near cursor; weak listening signal |
| Qt / GTK overlay | Heavy dependencies; overkill for MVP |

## Decision

Use a **small tkinter `Toplevel`** on a **dedicated thread** with a command queue:

- Show on `SessionState.LISTENING`, hide otherwise
- Position at cursor + configurable offset (`GetCursorPos` via ctypes)
- Horizontal level bar driven by existing RMS `current_level` (0–1)
- `-topmost` / `overrideredirect` for a borderless pill
- If creation fails: log once, set degraded flag, dictation continues

macOS/Linux: `CaptureIndicator` protocol + `NoOpIndicator` until platform impls land.

## Integration

- [`sybl/core/daemon.py`](../sybl/core/daemon.py) owns the indicator alongside hotkeys
- Reuses level polling already used for IPC/TUI (`_poll_levels`)
- Config: `[indicator]` in `config.toml` (`enabled`, `strategy`, `size_px`, offsets)

## Deferred

- Cursor-following every frame
- Waveform animation
- Tray icon fallback mode
- Sound cue on activate
