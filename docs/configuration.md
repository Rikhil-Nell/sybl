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
| `binding` | `"ctrl+alt+space"` | Push-to-talk chord |
| `mode` | `"ptt"` | Interaction mode (PTT only today) |
| `cancel_binding` | `"esc"` | Cancel while holding PTT |
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

## `[indicator]`

| Key | Default | Description |
| --- | --- | --- |
| `enabled` | `true` | Show listening pill while dictating |
| `strategy` | `"overlay"` | `"overlay"` or `"none"` |
| `size_px` | `48` | Pill size (pixels) |
| `offset_x` | `16` | Offset from cursor |
| `offset_y` | `16` | Offset from cursor |

On non-Windows platforms the overlay degrades to a no-op.

## CLI config commands

```powershell
sybl config init
sybl config show
sybl config set-key <provider>
sybl config vocab add|list|remove <term>
```

Changes made through the TUI are routed through the daemon so config stays authoritative.
