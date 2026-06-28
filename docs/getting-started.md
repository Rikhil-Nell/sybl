# Getting started

Navi is a background dictation daemon with a terminal UI. This guide covers a first
successful run on **Windows** (the primary platform).

## Install

Pick one:

```powershell
pipx install navi
```

```powershell
uv tool install navi
```

For development from source, see [DEVELOPMENT.md](DEVELOPMENT.md).

## Prerequisites

- Python **3.12+**
- A microphone
- An API key from [Groq](https://console.groq.com/) and/or [Deepgram](https://console.deepgram.com/)

## First run

### 1. Check your environment

```powershell
navi doctor
```

Fix anything flagged (missing deps, mic permissions, etc.) before continuing.

### 2. Initialize config

```powershell
navi config init
```

This creates `config.toml` under your Navi config directory (typically
`%APPDATA%\navi\config.toml` on Windows).

### 3. Store an API key

Keys live in the **OS keyring**, not in plaintext config:

```powershell
navi config set-key groq
# or
navi config set-key deepgram
```

### 4. Start the daemon

```powershell
navi start
```

The daemon listens for the global hotkey and owns the microphone. Leave this terminal
running (or run it in the background).

### 5. Attach the TUI (optional but recommended)

In a second terminal:

```powershell
navi tui
```

The TUI shows live logs, dictation state, transcription history, and settings. On
first run with no keys, a BYOK onboarding wizard appears.

## Dictate

1. Click into any text field (Notepad, browser, IDE, etc.).
2. Hold **Ctrl+Alt+Space** (default hotkey).
3. Speak your sentence.
4. Release the hotkey — Navi transcribes and pastes the result.

While holding the hotkey, press **Esc** to cancel before anything is pasted.

A small **listening pill** appears near your cursor on Windows while you hold the
hotkey.

## Other useful commands

```powershell
navi status          # Is the daemon running?
navi stop            # Stop the daemon
navi hotkey test     # Test bindings without STT
navi audio devices   # List input devices
navi transcribe --seconds 5   # One-shot record + transcribe (no daemon)
```

## Customize

- **Hotkey binding** — `[hotkey] binding` in `config.toml` (default avoids
  `ctrl+shift+space`, which Windows Terminal uses for a new window)
- **Provider** — `[provider] preferred` and model settings; see [providers.md](providers.md)
- **Vocabulary** — `navi config vocab add YourName`; see [configuration.md](configuration.md)

## Troubleshooting

| Symptom | Things to try |
| --- | --- |
| Nothing happens on hotkey | Is `navi start` running? Run `navi hotkey test`. Check binding conflicts. |
| No transcript / STT error | Run `navi doctor`; verify API key with `navi config set-key`. |
| Text not pasted | See [permissions.md](permissions.md); try `inject.enabled = true` in config. |
| Mic not detected | `navi audio devices`; set `[audio] device` in config. |

## Next steps

- [Providers](providers.md) — Groq vs Deepgram, streaming vs batch
- [Configuration](configuration.md) — full `config.toml` reference
- [Permissions](permissions.md) — mic access and paste injection
