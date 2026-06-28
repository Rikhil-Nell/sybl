# Navi

Open-source, bring-your-own-key (BYOK) voice dictation. Put your cursor anywhere,
hit a global shortcut, speak, and Navi transcribes it and types it in for you.

## Quick start

```powershell
uv sync
uv run navi doctor
uv run navi config init
uv run navi config set-key groq
uv run navi start
```

## Test audio capture (Phase 1)

```powershell
uv run navi audio devices
uv run navi audio record --seconds 3
```

Record for a few seconds — you should see a live level meter that responds
when you speak. Debug WAV files are saved under your Navi state directory in
`debug recording/` (default: `last_recording.wav`).

## Transcribe speech (Phase 2 + 3)

Store provider API keys in the OS keyring, then record and transcribe:

```powershell
uv run navi config set-key groq
uv run navi transcribe --seconds 5

uv run navi config set-key deepgram
uv run navi transcribe --seconds 5 --stream
```

Batch mode (default) sends captured audio to Groq. `--stream` uses Deepgram's
WebSocket API for live partial transcripts while you speak.

Configure models in `config.toml`:

- `[provider.groq]` — default `whisper-large-v3-turbo` (speed) or `whisper-large-v3` (accuracy)
- `[provider.deepgram]` — default `nova-3`; set `interim_results = true` for streaming partials

Provider fallback order is configurable under `[provider]` (`preferred`, `fallback_order`).

## Global hotkeys (Phase 4)

Start the daemon and dictate from anywhere with push-to-talk:

```powershell
uv run navi config set-key groq
uv run navi start
```

Hold `ctrl+alt+space` (default binding), speak, release — the transcript is pasted
into whatever app had focus when you pressed the hotkey. Press `Esc` while holding
to cancel.

The default avoids `ctrl+shift+space`, which Windows Terminal uses for a new
window. Change `binding` under `[hotkey]` in `config.toml` if you prefer something else.

Test bindings without STT:

```powershell
uv run navi hotkey test
```

Configure under `[hotkey]` in `config.toml`:

- `binding` — default `ctrl+alt+space` (not `ctrl+shift+space`; that opens a new Windows Terminal window)
- `cancel_binding` — default `esc`
- `streaming` — `auto`, `on`, or `off` (auto streams when the resolved provider supports it)
- `min_duration_ms` — skip accidental taps shorter than this

Configure injection under `[inject]`:

- `enabled` — default `true` (set `false` to log transcripts only)
- `strategy` — default `paste` (clipboard + Ctrl+V)
- `restore_clipboard` — default `true` (put your prior clipboard back after paste)

Configure post-processing under `[postprocess]`:

- `enabled` — default `true`
- `trim_fillers` — remove leading/trailing "um", "uh", etc.
- `capitalize` — capitalize the first letter
- `ensure_punctuation` — default `false` (adds `.` when missing)

## Phase 9 — Dictation quality (Phase 9)

Teach STT your names and jargon, tighten cleanup rules, and use spoken commands in the final transcript.

### Custom vocabulary (STT hints)

Add terms passed to Deepgram keyterms / Groq Whisper prompt at each session start:

```powershell
uv run navi config vocab add Rikhil
uv run navi config vocab add Navi
uv run navi config vocab list
```

Stored in `vocabulary.toml` under your Navi state directory. Disable with
`vocabulary.enabled = false` in `config.toml`.

### Voice commands

Parsed from the **final** transcript after post-processing (works in batch and streaming):

- `new line` / `newline` — inserts a line break
- `period` / `comma` — inserts `.` / `,`

To cancel before anything is transcribed or pasted, press **Esc** while holding
the hotkey. Transcripts always land in TUI history after STT completes.

Disable with `voice_commands.enabled = false`.

### Extended post-processing

Additional optional passes under `[postprocess]`:

- `collapse_repeated_words` — default `false`
- `normalize_quotes` — default `true`
- `trim_space_before_punctuation` — default `true`

## Daemon + TUI (Phase 6 + 7)

Run the daemon in one terminal, attach the TUI in another:

```powershell
# Terminal A
uv run navi start

# Terminal B
uv run navi tui
```

Other daemon commands:

```powershell
uv run navi status
uv run navi stop
```

The TUI shows live logs, dictation state, transcription history, and in-app settings
(provider, API keys, post-processing). On first run with no keys configured, a BYOK
onboarding wizard appears.

While dictating, a **small listening pill** appears near your cursor (Windows
overlay, enabled by default). It shows live mic level and hides when you release
the hotkey. Disable with `indicator.enabled = false` in config.

Optional: run the full test suite (excludes mic hardware and live API tests):

```powershell
uv run pytest -m "not integration"
```

To include real-hardware or live-provider integration tests:

```powershell
uv run pytest -m integration
```

See [AGENTS.md](AGENTS.md) for the project mission and [docs/ROADMAP.md](docs/ROADMAP.md)
for the phased plan.
