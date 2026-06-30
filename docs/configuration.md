# Configuration reference

sybl reads `config.toml` from your platform config directory (via `platformdirs`).
Run `sybl config init` to create defaults.

State files (vocabulary, daemon socket info, logs, debug recordings) live in a
separate state directory under the same app name (`sybl`).

## `[provider]`

| Key | Default | Description |
| --- | --- | --- |
| `preferred` | `"groq"` | Provider id used first at session start |
| `fallback_order` | `["deepgram", "groq"]` | Try these if preferred is unavailable |

### `[provider.groq]`

| Key | Default | Description |
| --- | --- | --- |
| `model` | `"whisper-large-v3-turbo"` | Groq Whisper model id |
| `language` | `null` | ISO language code or null for auto |
| `prompt` | `null` | Extra Whisper prompt (vocab merged at runtime) |
| `temperature` | `0.0` | Sampling temperature |

### `[provider.deepgram]`

| Key | Default | Description |
| --- | --- | --- |
| `model` | `"nova-3"` | Deepgram model |
| `language` | `null` | Language code or null |
| `punctuate` | `true` | Punctuation |
| `smart_format` | `true` | Smart formatting |
| `interim_results` | `true` | Partial transcripts while streaming |

## `[hotkey]`

| Key | Default | Description |
| --- | --- | --- |
| `binding` | `"ctrl+alt+space"` | Activation chord |
| `mode` | `"both"` | `"ptt"`, `"toggle"`, or `"both"` (hold + double-press together) |
| `cancel_binding` | `"esc"` | Cancel while listening |
| `ptt_hold_ms` | `200` | In `both` mode, hold this long before PTT starts (avoids toggle clash) |
| `toggle_double_press_ms` | `400` | Max gap between chord presses for toggle start (200–1000) |
| `streaming` | `"auto"` | `"auto"`, `"on"`, or `"off"` |
| `min_duration_ms` | `250` | Ignore taps shorter than this |

Avoid `ctrl+shift+space` on Windows — Windows Terminal binds it to a new window.

## `[inject]`

| Key | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Paste transcript at cursor |
| `strategy` | `"paste"` | Clipboard + simulated Ctrl+V (Windows) |
| `restore_clipboard` | `true` | Restore clipboard after paste |

Set `enabled = false` to log transcripts only (useful for debugging STT).

## `[postprocess]`

Rule-based cleanup between STT and injection:

| Key | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Master switch |
| `trim_fillers` | `true` | Trim leading/trailing um/uh |
| `capitalize` | `true` | Capitalize first letter |
| `ensure_punctuation` | `false` | Append `.` if missing |
| `collapse_repeated_words` | `false` | Collapse stuttered words |
| `normalize_quotes` | `true` | Straighten smart quotes |
| `trim_space_before_punctuation` | `true` | `word .` → `word.` |
| `collapse_duplicate_punctuation` | `true` | `..` → `.`, `,,` → `,` |

## `[vocabulary]`

| Key | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Pass terms to STT as hints |

Manage terms via CLI (stored in `vocabulary.toml`):

```powershell
sybl config vocab add sybl
sybl config vocab list
sybl config vocab remove sybl
```

## `[voice_commands]`

| Key | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Parse spoken commands in final transcript |

Supported phrases: `new line` / `newline`, `period`, `comma`.

## `[audio]`

| Key | Default | Description |
| --- | --- | --- |
| `device` | `null` | Device name or index; null = default |
| `sample_rate` | `16000` | Target sample rate (Hz) |
| `channels` | `1` | Mono |
| `block_duration_ms` | `20` | Capture block size |
| `save_last_recording` | `true` | Save debug WAV under state dir |

## `[logging]`

| Key | Default | Description |
| --- | --- | --- |
| `level` | `"INFO"` | Log level |
| `ring_buffer_size` | `500` | In-memory log ring for TUI |

## `[ipc]`

| Key | Default | Description |
| --- | --- | --- |
| `host` | `"127.0.0.1"` | Daemon bind address |
| `command_port` | `0` | Auto-assign if 0 |
| `event_port` | `0` | Auto-assign if 0 |
| `history_size` | `100` | Transcript history cap |

## `[ui]`

| Key | Default | Description |
| --- | --- | --- |
| `onboarding_complete` | `false` | BYOK wizard shown until true |
| `first_run_shown` | `false` | ASCII CLI banner shown once until true |

## `[indicator]`

| Key | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Show listening indicator while dictating |
| `strategy` | `"pill"` | `"pill"` (Qt dock pill, Windows), or `"none"`. Legacy `"overlay"` / `"orb"` → `"pill"`. |
| `size_px` | `72` | Reserved for future pill sizing (pixels) |
| `offset_x` | `16` | Reserved (legacy tk cursor offset) |
| `offset_y` | `16` | Reserved (legacy tk cursor offset) |
| `anchor` | `"top_center"` | Screen anchor: `top_center` (dock pill), `top_right`, `top_left`, `bottom_right`, `bottom_left`, `cursor` |
| `margin_px` | `0` | Margin from top work-area edge for dock pill (0–256) |
| `orb_accent` | `"#7b2ff7"` | Primary wave color (hex, purple) |
| `orb_accent_secondary` | `"#f97316"` | Secondary wave color (hex, orange) |
| `orb_idle_opacity` | `0.55` | Reserved for future idle styling (0.0–1.0) |
| `orb_fps` | `30` | Animation frame rate (15–60) |
| `sound_enabled` | `false` | Two-note chime on listen start/stop (cross-platform) |
| `sound_on_start` | `true` | Play cue when listening begins |
| `sound_on_stop` | `true` | Play cue when listening ends |
| `sound_volume` | `0.75` | Chime loudness (`0.0`–`1.0`) |
| `sound_start_file` | *(unset)* | Optional WAV filename or path for listen-start cue |
| `sound_stop_file` | *(unset)* | Optional WAV filename or path for listen-stop cue |
| `sound_max_seconds` | `0.5` | Max cue length; longer files are trimmed automatically (up to `2.0`) |

### Custom sound cues

On `sybl config init`, sybl creates a **`sounds/`** folder next to `config.toml`:

```
%LOCALAPPDATA%\sybl\sybl\
  config.toml
  sounds\
    README.txt
    start.wav   # optional — plays when listening begins
    stop.wav    # optional — plays when listening ends
```

Enable with `sound_enabled = true`. If a file is missing, sybl falls back to the
built-in two-note chime. Files longer than `sound_max_seconds` are trimmed — no need
to edit them down first. Override filenames with `sound_start_file` / `sound_stop_file`
(relative to the sounds folder, or an absolute path).

**TUI:** `sybl tui` → Settings (`s`) — toggle sound, set volume, browse or paste a path
to import WAV files, or pick **Built-in chime** per cue.

On non-Windows platforms the listening pill degrades to a no-op (dictation unaffected).
See [OVERLAY.md](OVERLAY.md).

Example — customize pill colors:

```toml
[indicator]
strategy = "pill"
anchor = "top_center"
margin_px = 0
orb_accent = "#7b2ff7"
orb_accent_secondary = "#f97316"
```

Or via CLI:

```powershell
sybl config set indicator.orb_accent "#7b2ff7"
```

## CLI config commands

```powershell
sybl config init
sybl config show
sybl config show --json
sybl config get <dotted.path>
sybl config set <dotted.path> <value>
sybl config edit
sybl config set-key <provider>
sybl config keys
sybl config vocab add|list|remove <term>
```

See [CLI.md](CLI.md) for the full command reference, `--json` outputs, and exit codes.

Changes made through the TUI or `config set` (while the daemon runs) are routed through
the daemon so config stays authoritative.
