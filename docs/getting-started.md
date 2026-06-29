# Getting started

sybl is a background dictation daemon with a terminal UI. This guide covers a first
successful run on **Windows** (the primary platform).

## Install

Pick one:

```powershell
pipx install sybl
```

```powershell
uv tool install sybl
```

First install pulls ~45 Python packages — allow 1–3 minutes on a cold install.

For development from source, see [DEVELOPMENT.md](DEVELOPMENT.md).

## Prerequisites

- Python **3.12+**
- A microphone
- An API key from [Groq](https://console.groq.com/) and/or [Deepgram](https://console.deepgram.com/)

## First run

### 1. Check your environment

```powershell
sybl doctor
```

For network, mic, and clipboard probes: `sybl doctor --live` (needs API key and mic).

Fix anything flagged (missing deps, mic permissions, etc.) before continuing.

### 2. Initialize config

```powershell
sybl config init
```

This creates `config.toml` and a **`sounds/`** folder under your sybl config directory
(typically `%LOCALAPPDATA%\sybl\sybl\` on Windows). Drop `start.wav` and `stop.wav`
there for custom listen cues, or import them from **TUI Settings** (`sybl tui` → `s`).

### 3. Store an API key

Keys live in the **OS keyring**, not in plaintext config:

```powershell
sybl config set-key groq
# or
sybl config set-key deepgram
```

### 4. Start the daemon

```powershell
sybl start
```

This starts sybl in the **background** and returns your terminal. Logs go to the log
file shown on startup. Stop with `sybl stop`.

For debugging (blocks the terminal, prints logs to stderr):

```powershell
sybl start --foreground
```

### 5. Attach the TUI (optional but recommended)

```powershell
sybl tui
```

The TUI shows live logs, dictation state, transcription history, and settings. On
first run with no keys, a BYOK onboarding wizard appears.

## Dictate

Default hotkey mode is **`both`** (Wispr-style): push-to-talk and toggle on the same
binding.

### Push-to-talk

1. Click into any text field.
2. **Hold** **Ctrl+Alt+Space** (~200ms in `both` mode, immediately in `ptt`-only mode).
3. Speak, then **release** — sybl transcribes and pastes.

### Toggle (hands-free)

1. **Double-press** **Ctrl+Alt+Space** quickly (within 400ms by default).
2. Speak — recording continues after you release the keys.
3. **Press the hotkey once** while listening to stop and paste.

### Config

In `config.toml`:

```toml
[hotkey]
mode = "both"              # ptt | toggle | both (default: both)
binding = "ctrl+alt+space"
ptt_hold_ms = 200          # both mode only — hold before PTT fires
toggle_double_press_ms = 400
```

Or change mode/binding in the TUI: `sybl tui` → **Settings** (`s`).

Press **Esc** while listening to cancel before paste.

A small **listening pill** follows your cursor on Windows while dictating. Optional
**sound cues** play on listen start/stop — configure in TUI Settings or
`[indicator]` in config; see [configuration.md](configuration.md).

## Other useful commands

```powershell
sybl status          # Is the daemon running?
sybl stop            # Stop the daemon
sybl hotkey test     # Test bindings without STT
sybl audio devices   # List input devices
sybl transcribe --seconds 5   # One-shot record + transcribe (no daemon)
```

## Customize

- **Hotkey binding / mode** — TUI Settings (`s`) or `[hotkey]` in `config.toml`
- **Sound cues** — TUI Settings (browse/import WAV, volume) or `sounds/start.wav` /
  `sounds/stop.wav`; see [configuration.md](configuration.md)
- **Provider** — `[provider] preferred` and model settings; see [providers.md](providers.md)

## Troubleshooting

| Symptom | Things to try |
| --- | --- |
| Nothing happens on hotkey | Is `sybl start` running? Run `sybl hotkey test`. Check binding conflicts. |
| No transcript / STT error | Run `sybl doctor`; verify API key with `sybl config set-key`. |
| Text not pasted | See [permissions.md](permissions.md); try `inject.enabled = true` in config. |
| Mic not detected | `sybl audio devices`; set `[audio] device` in config. |

## Next steps

- [Providers](providers.md) — Groq vs Deepgram, streaming vs batch
- [Configuration](configuration.md) — full `config.toml` reference
- [Permissions](permissions.md) — mic access and paste injection
