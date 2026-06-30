# sybl user guide

Everything you need to install, configure, and dictate with sybl on **Windows**
(the primary platform for the full core loop).

---

## Install

```powershell
pipx install sybl
# or
uv tool install sybl
```

Requires **Python 3.12+**. First install pulls ~45 packages — allow 1–3 minutes.

## First run

```powershell
sybl doctor
sybl setup                    # interactive wizard (TTY)
# or manually:
sybl config init
sybl config set-key groq
sybl start
sybl tui                      # optional dashboard
```

Keys live in the **OS keyring**, never in `config.toml`. Config path:
`sybl config path` (typically `%LOCALAPPDATA%\sybl\sybl\config.toml` on Windows).

---

## Dictation

Default hotkey: **Ctrl+Alt+Space** in **`both`** mode (push-to-talk + toggle).

| Mode | How |
| --- | --- |
| Push-to-talk | Hold the hotkey ~200 ms, speak, release |
| Toggle | Double-press quickly, speak, press once to stop |
| Cancel | **Esc** while listening (before paste) |

While listening, a **dock pill** appears at the top center of the screen (wave bars,
timer, transcribing spinner). Disable with `indicator.strategy = "none"`.

---

## Providers (BYOK)

| Provider | Style | Good for |
| --- | --- | --- |
| **Groq** | Batch Whisper | Fast setup, PTT |
| **Deepgram** | Streaming + batch | Partials, lower latency |

```powershell
sybl config set-key groq
sybl config set-key deepgram
sybl config set provider.preferred groq
```

```toml
[provider]
preferred = "groq"
fallback_order = ["deepgram", "groq"]

[provider.groq]
model = "whisper-large-v3-turbo"

[provider.deepgram]
model = "nova-3"
interim_results = true
```

Test without the daemon: `sybl transcribe --seconds 5` (add `--stream` for Deepgram).

**Vocabulary hints** (names, jargon): `sybl config vocab add MyTerm` — sent to the
provider at session start.

**Voice commands** on final transcript: `new line`, `period`, `comma`.

---

## CLI commands

Run bare `sybl` for categorized help.

| Panel | Commands |
| --- | --- |
| Daemon | `start`, `stop`, `restart`, `status`, `logs` |
| Dictation | `audio`, `transcribe`, `hotkey test`, `indicator demo` |
| Config | `config`, `setup`, `providers` |
| Diagnostics | `doctor`, `tui` |

Useful flags:

```powershell
sybl --no-input              # scripts/agents — no prompts
sybl status --json
sybl doctor --live           # mic + network + clipboard probes
sybl config get hotkey.mode
sybl config set hotkey.mode both
sybl config edit             # $EDITOR → reload daemon
sybl logs --follow
sybl tui --demo              # UI preview without daemon
```

**Exit codes:** `0` ok · `3` daemon down · `4` config error · `5` IPC error · `6` keyring error

When the daemon is running, `config set` and TUI settings patch the live daemon.

---

## TUI dashboard

```powershell
sybl tui
```

| Key | Action |
| --- | --- |
| `s` | Settings (all config via daemon) |
| `e` | Edit `config.toml` in `$EDITOR` |
| `?` | Help |
| `/` | Filter transcripts |
| `y` | Copy selected transcript |
| `q` | Quit TUI (daemon keeps running) |

---

## Configuration reference

Run `sybl config show` for the full effective config. Key sections:

### `[hotkey]`

| Key | Default | Notes |
| --- | --- | --- |
| `binding` | `ctrl+alt+space` | Avoid `ctrl+shift+space` (Windows Terminal conflict) |
| `mode` | `both` | `ptt`, `toggle`, or `both` |
| `cancel_binding` | `esc` | Cancel while listening |
| `ptt_hold_ms` | `200` | Hold threshold in `both` mode |
| `toggle_double_press_ms` | `400` | Double-press window |
| `streaming` | `auto` | `auto`, `on`, or `off` |

### `[inject]`

| Key | Default |
| --- | --- |
| `enabled` | `true` |
| `strategy` | `paste` (clipboard + Ctrl+V) |
| `restore_clipboard` | `true` |

Set `enabled = false` to debug STT without pasting.

### `[postprocess]`

Whitespace trim, filler trim, capitalize, optional punctuation — all under
`[postprocess]` in config. Enabled by default except `ensure_punctuation`.

### `[indicator]`

| Key | Default | Notes |
| --- | --- | --- |
| `enabled` | `true` | Listening pill |
| `strategy` | `pill` | `pill` or `none` |
| `anchor` | `top_center` | Dock placement |
| `margin_px` | `0` | Inset from top edge |
| `orb_accent` | `#7b2ff7` | Wave color (legacy key name) |
| `sound_enabled` | `false` | Start/stop chime |

Custom WAV cues: drop `start.wav` / `stop.wav` in the `sounds/` folder next to
`config.toml`, or import from TUI Settings.

### `[audio]`

| Key | Default |
| --- | --- |
| `device` | `null` (system default) |
| `save_last_recording` | `true` (debug WAV in state dir) |

---

## Permissions and privacy

**Windows:** allow microphone in Settings → Privacy. Injection uses clipboard +
simulated Ctrl+V — works in most text fields; fails in some secure/elevated apps.

**macOS / Linux:** daemon and CLI run; hotkeys, injection, and the pill are not
ported yet.

- API keys: OS keyring only (`sybl config set-key`)
- Audio: sent to your STT provider during active sessions only
- No sybl telemetry or cloud transcript storage
- Report vulnerabilities: [SECURITY.md](../SECURITY.md)

---

## Troubleshooting

| Symptom | Try |
| --- | --- |
| Hotkey does nothing | `sybl status` · `sybl hotkey test` · binding conflicts |
| STT errors | `sybl doctor` · `sybl config set-key` · check provider credits |
| No paste | `inject.enabled` · elevated app focus · copy from TUI history |
| No mic | `sybl audio devices` · set `[audio] device` · Windows mic privacy |

---

## Platform status

| | Windows | macOS / Linux |
| --- | --- | --- |
| Hotkeys | Yes | Planned |
| Injection | Yes | Planned |
| Listening pill | Yes | Planned |
| Daemon + TUI + CLI | Yes | Yes |

Contributors: see [CONTRIBUTING.md](../CONTRIBUTING.md) and [AGENTS.md](../AGENTS.md).
