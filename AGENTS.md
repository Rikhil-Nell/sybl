# AGENTS.md

> Living source of truth for the sybl project. Read this first. Keep it current.
> Last updated: 2026-06-29 (Cursor Cloud env setup notes)

---

## 1. Mission

**sybl is an open-source, bring-your-own-key (BYOK) voice dictation tool.**

Put your cursor anywhere, hit a global shortcut, speak/ramble into a lightweight
popup, and sybl transcribes it fast and types it in for you — wherever you were
about to type. It is the open-source answer to closed tools like Wispr Flow.

The guiding principles:

- **BYOK, provider-agnostic.** Users plug in whatever speech-to-text (STT)
  credits they already have — Deepgram, AssemblyAI, Gladia, Groq (Whisper
  large-v3), etc. No vendor lock-in, no sybl-hosted backend, no subscription.
- **Local-first & private.** Audio goes straight from the user's machine to the
  STT provider of their choice. sybl keeps no telemetry and stores nothing it
  doesn't have to.
- **Fast & invisible.** Dictation should feel instant and stay out of the way.
- **TUI, daemon-based.** sybl runs as a background daemon. All of its UI is a
  terminal UI (TUI): live logs, status, history, and config — nothing more.

## 2. What sybl Does (Product Spec)

- **Global activation.** A system-wide shortcut works regardless of focused app.
- **Two interaction modes (same binding by default):**
  - **Push-to-talk (PTT):** hold the shortcut, speak, release to finish.
  - **Toggle / constant recording:** a double-press of the shortcut starts
    continuous recording; press again to stop.
  - Default **`both`** mode enables PTT and toggle together (Wispr-style).
- **Popup capture surface.** When activated, a small on-screen pill appears near the
  cursor so the user knows sybl is listening (Windows tkinter overlay MVP; see
  `docs/POPUP-SPIKE.md`).
- **BYOK transcription.** Audio is streamed/sent to the user's selected provider
  and transcribed quickly.
- **Text injection.** The transcript is inserted at the current cursor location
  in whatever app had focus when activation happened.
- **TUI surface.** A Textual-based TUI shows live logs, current state, and a
  scrollback history of recent transcriptions for reference.

## 3. Current State

> Update this section every time the project's reality changes.

- **Phase:** v0.1.1 ready to ship — both/toggle hotkey modes, background `sybl start`,
  custom sound cues (`sounds/` + TUI import), cursor-following indicator pill,
  `sybl doctor --live`, Hermes-shaped contributor hygiene, TUI IPC stability.
- **Next releases:** **v0.1.2** — heavy TUI overhaul (modal UX, live meter, instant
  attach, design system). **v0.2.0** — new providers, macOS/Linux backends, native
  helpers. See `docs/ROADMAP.md`.
- **Code:** `sybl/audio/` implements `AudioCaptureSession` (sounddevice callback →
  asyncio queue, 16 kHz mono int16, resampling, dBFS peak metering, debug WAV save).
  `sybl/providers/` implements streaming-first STT interface, `ProviderCapabilities`,
  `resolve_provider` session-start selection, `GroqProvider` (batch), and
  `DeepgramProvider` (WebSocket streaming + REST batch via official SDK).
  `sybl/hotkeys/` implements `HotkeyManager`, binding parser, Windows `pynput` PTT,
  toggle, and **`both`** (Wispr-style) backends, and focus capture at activation. `sybl/inject/` implements `TextInjector`,
  Windows clipboard-paste injection with focus restore and clipboard restoration.
  `sybl/core/` has `StateMachine`, `DictationController`, `SyblDaemon`, post-processing,
  voice commands, `TranscriptHistory`, `EventBus`, and transcribe pipeline.
  `sybl/config/vocabulary.py` stores STT hint terms. `sybl/ipc/` implements
  NDJSON command/event TCP servers and client. `sybl/tui/` is a Textual app (logs,
  status, history, settings, BYOK onboarding). `sybl/indicator/` implements
  `CaptureIndicator` (NoOp + Windows tkinter overlay near cursor with RMS level bar).
  CLI: `sybl start`, `sybl stop`, `sybl status`, `sybl tui`, `sybl config`,
  `sybl config vocab`, `sybl doctor`, `sybl audio`, `sybl transcribe`, `sybl hotkey test`.
  `sybl start` detaches by default; `--foreground` blocks for debug.
- **Stack pinned:** `typer`, `pydantic`, `platformdirs`, `keyring`, `tomli-w`,
  `sounddevice`, `numpy`, `soundfile`, `soxr`, `groq`, `tenacity`, `deepgram-sdk`,
  `pynput`, `textual`; dev: `ruff`, `pytest`, `pytest-asyncio`.
- **Primary platform:** Windows first (dev machine). Code stays cross-platform
  behind interfaces, but the core loop is proven on Windows before expanding.
- **Open questions:** per-platform overlay beyond Windows; text-injection
  edge cases (Wayland especially); how aggressive default post-processing should
  be.

## 4. Architecture & Tech Decisions

> A decision log. Append new decisions; don't silently rewrite history.

| Area | Decision | Rationale |
|------|----------|-----------|
| Language | Python 3.12 | Already scaffolded; first-class STT SDKs; great TUI ecosystem. |
| Packaging / env | `uv` + `pyproject.toml` | Already in place; fast, reproducible. |
| TUI framework | Textual (pinned) | Modern, async, rich rendering for logs/history; `sybl tui` attaches over IPC. |
| Audio capture | `sounddevice` + **callback → queue** pattern | PortAudio bindings, NumPy-friendly; callback pushes int16 PCM to an `asyncio.Queue`; never block or process in the callback. |
| Audio format | **16 kHz, mono, int16 PCM** | What most STT providers expect; resample in-pipeline if the device opens at 48 kHz. |
| Daemon concurrency | **`asyncio` event loop** + dedicated audio thread | Daemon/TUI/async providers run on asyncio; sounddevice callback thread only enqueues chunks. |
| Global hotkeys | `pynput` for **MVP**, behind `HotkeyManager` interface | Fast to ship on Windows; plan migration to a small **native helper** (e.g. Rust `global-hotkey`) if reliability stalls. Avoid the `keyboard` library (security/root issues). |
| STT providers | Pluggable, **streaming-first** interface | Core BYOK requirement; designing for streaming up front avoids rework when batch is the easy case. |
| Reference provider | **Deepgram** (streaming) as reference; **Groq Whisper** (batch) as early sanity check | Deepgram's streaming is fast/feature-rich and makes the cleanest reference; Groq gives the fastest first end-to-end signal as a degenerate batch case behind the same interface. |
| Groq integration | Official **`groq` SDK** + in-memory WAV upload via `asyncio.to_thread()` | OpenAI-compatible transcriptions endpoint; default model `whisper-large-v3-turbo`; PCM→WAV matches Groq's 16 kHz mono expectation. |
| Deepgram integration | Official **`deepgram-sdk`** — WebSocket `wss://api.deepgram.com/v1/listen` for streaming, REST `/v1/listen` for batch | Raw linear16 PCM at 16 kHz mono on websocket; `interim_results=true` for partials; `CloseStream` on end; default model `nova-3`. |
| Process model | Background daemon + TUI client over local IPC | Daemon listens for hotkeys always; TUI attaches on demand. |
| Daemon authority | Daemon is the **single source of truth** | Owns mic, providers, state machine, injection, config; TUI is a thin observe/command client. Config changes flow through the daemon so they persist and take effect immediately (no TUI/daemon drift). |
| IPC shape | Simple command/response + a separate log/event stream; ring buffer for logs & history | More maintainable than sharing complex objects across processes; predictable memory; clean TUI reconnects. |
| STT interface shape | **Async generators** yielding `TranscriptionResult` | `async def transcribe(audio: bytes \| AsyncIterable[bytes]) -> AsyncGenerator[TranscriptionResult, None]` with `text`, `is_final`, optional `confidence`. |
| STT errors/retries | Custom exception hierarchy + **`tenacity`** | Normalize `STTError`, `STTTimeoutError`, `STTRateLimitError`; retry only transient failures. |
| Provider selection | **`ProviderManager`** above providers | Registry + capability flags + config-driven fallback at **session start** (not mid-stream). |
| Config validation | **Pydantic** models | Schema validation and sane defaults for provider/device settings. |
| Text injection | **Clipboard set + simulated paste = primary**; synthetic keystrokes = labeled secondary/experimental | Paste is the most forgiving path in pure Python; restore prior clipboard after. Wispr-level reliability eventually needs **native injection** (Win `SendInput`, macOS `CGEvent`) — document limitations until then. |
| Hotkey escape hatch | If `pynput` reliability becomes a recurring problem, introduce a small **native component** (Rust `global-hotkey` or similar) rather than fighting Python libs | Commercial tools use native code per OS; pure Python won't match Wispr Flow on hotkeys/injection long-term. |
| Signal metering | **RMS level** for UI now; proper **VAD later** | RMS feeds the popup/TUI meter; `webrtcvad` or `silero-vad` when we need to avoid cutting off speech or trailing silence. |
| Core concerns | State machine + post-processing pipeline are **first-class from early on** | They sit at the center of UX and the core text path; easier to refine while surrounding plumbing is still simple. |
| Secrets | OS keyring via `sybl.secrets` | Keep API keys out of plaintext config; `sybl config set-key`. |
| CLI | Typer subcommands | `start`, `stop`, `status`, `tui`, `config`, `doctor`, `audio`, `transcribe`, `hotkey`. |
| Logging | File + console + ring buffer | `sybl.logging.setup_logging`; ring buffer for future TUI tail. |
| Phase 4 hotkeys | **PTT-first** via `pynput` behind `HotkeyManager`; focus captured at **activation press** | Reliability anchor before toggle mode; HWND stored for Phase 5 injection; Windows-only MVP. |
| Phase 5 injection | **Clipboard set + simulated Ctrl+V** via `SendInput` (ctypes); restore prior clipboard; focus restore with thread attach | Primary strategy on Windows; avoids pynput paste deadlock with hotkey listener; no new deps. |
| Phase 5.5 post-processing | **Rule-based pipeline** (`PostProcessConfig` + ordered passes) between STT and inject | Whitespace, filler trim, capitalize on by default; auto-punctuation off; Phase 9 expands without restructuring. |
| Phase 6 IPC | **TCP localhost NDJSON** — separate command + event ports; `daemon.json` + PID lock | Cross-platform; asyncio-native; TUI/CLI attach without shared memory. |
| Phase 7 TUI | **Textual dashboard** — logs, status, history, settings, BYOK onboarding | All config/key writes routed through daemon IPC; keyboard-driven MVP. |
| Phase 8 indicator | **Windows tkinter overlay** on dedicated thread; `CaptureIndicator` protocol + `NoOpIndicator` elsewhere | Stdlib, no new deps; cursor position via ctypes; show on LISTENING, RMS level bar; degrade to no-op if tk fails (`docs/POPUP-SPIKE.md`). |
| Phase 9 vocabulary | **STT hints only** — `vocabulary.toml` + Deepgram keyterms + Groq prompt at session start | Names/jargon at transcription source; no post-STT replacement map; term list reused by future LLM pass. |
| Phase 9 voice commands | **Final-transcript parsing** — `new line`, `period`, `comma` | No streaming/wake-word; Esc cancels before STT/inject; no scratch-that erase. |
| Phase 10 OSS | **MIT license**, PyPI + `pipx`/`uv tool` primary install, GitHub issue/PR templates, CI on Windows+Ubuntu | Hermes-style contributor surface without a separate docs site; `docs/` hub + README landing page. |
| Phase 10 PyPI | **`release.yml`** on GitHub Release → `uv build` → PyPI trusted publishing (OIDC) | No long-lived PyPI token in repo; maintainers configure pending publisher on PyPI. |
| v0.1.1 hygiene | **`scripts/run_tests.py`**, dep `<next_major` caps, unixisms CI, AGENTS rubric | Hermes-shaped contributor surface; hermetic tests via `SYBL_CONFIG_DIR` / `SYBL_STATE_DIR`. |
| v0.1.1 toggle | **`HotkeyConfig.mode` `toggle`** — double-press chord to start, single press to stop | Same `HotkeyEvent` semantics for dictation core. |
| v0.1.1 both mode | **`HotkeyConfig.mode` `both` (default)** — hold = PTT after `ptt_hold_ms`; double-press = toggle on same binding | Wispr-style; `ptt`/`toggle` remain for single-mode users. |
| v0.1.1 background | **`sybl start` detached by default** — `sybl/daemon/spawn.py`; `--foreground` for debug | TUI is the primary log surface; file log always on. systemd/launchd wrap same command. |
| v0.1.1 indicator chime | **Custom WAV cues** in `{config_dir}/sounds/` with auto-trim (`sound_max_seconds`); built-in chime fallback | Cross-platform via `sounddevice`; no per-OS sound APIs. |
| v0.1.1 secrets docs | Keyring threat model in `docs/permissions.md`; **`sybl doctor --live`** for probes | Live checks opt-in; static doctor stays CI-safe. |
| Rebrand | **sybl** everywhere — Python package `sybl/`, CLI **`sybl`**, PyPI **`sybl`**, app id `sybl` | Prior names `navi` and `sybil`/`sybil-dictation` were taken or conflicted on PyPI; `sybl` is the canonical name. |

High-level component map:

```
                 +-------------------+
  global hotkey  |   Hotkey Listener |
  ───────────────▶  (PTT / toggle)  │
                 +---------+---------+
                           │ activate
                           ▼
+-----------+      +-------+-------+      +------------------+
|  Audio    |─────▶|  Daemon Core  |─────▶|  STT Provider    |
|  Capture  | PCM  | (state machine)| audio|  (BYOK, pluggable)|
+-----------+      +-------+-------+      +--------+---------+
                           │  transcript          │ text
                           ▼                       │
                  +--------+--------+◀─────────────+
                  | Text Injection  |
                  | (cursor target) |
                  +-----------------+
                           ▲
         +-----------------+------------------+
         │ IPC (logs/state/history)           │
+--------+--------+              +-----------+-----------+
|   TUI Client    |              | Capture Indicator     |
| (Textual app)   |              | (listening pill, Win) |
+-----------------+              +-----------------------+
```

## 5. Project Structure

> Keep this in sync with the real tree as it grows.

```
sybl/
├── AGENTS.md
├── README.md
├── LICENSE
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── SECURITY.md
├── CHANGELOG.md
├── .github/
│   ├── ISSUE_TEMPLATE/
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── workflows/          # ci.yml, release.yml
├── .githooks/              # optional commit-msg hook (no Cursor co-author)
├── docs/
│   ├── getting-started.md
│   ├── providers.md
│   ├── configuration.md
│   ├── permissions.md
│   ├── DEVELOPMENT.md
│   ├── DAEMON.md
│   ├── POPUP-SPIKE.md
│   ├── ROADMAP.md
│   └── RESEARCH-NOTES.md
├── scripts/               # run_tests.py, check_unixisms.py
├── main.py                # legacy redirect to CLI
├── pyproject.toml
├── tests/
│   ├── conftest.py
│   ├── test_audio.py
│   ├── test_bindings.py
│   ├── test_cli.py
│   ├── test_config.py
│   ├── test_deepgram.py
│   ├── test_dictation.py
│   ├── test_doctor.py
│   ├── test_daemon_indicator.py
│   ├── test_history.py
│   ├── test_hotkeys.py
│   ├── test_indicator.py
│   ├── test_indicator_sound.py
│   ├── test_inject.py
│   ├── test_ipc_protocol.py
│   ├── test_ipc_server.py
│   ├── test_logging.py
│   ├── test_manager.py
│   ├── test_postprocess.py
│   ├── test_providers.py
│   ├── test_secrets.py
│   ├── test_single_instance.py
│   ├── test_transcribe.py
│   ├── test_tui_client.py
│   ├── test_tui_settings.py
│   ├── test_vocabulary.py
│   ├── test_voice_commands.py
│   └── test_provider_vocabulary.py
└── sybl/
    ├── __init__.py
    ├── __main__.py
    ├── cli/               # start, stop, status, tui, config, doctor, audio, transcribe, hotkey
    ├── config/            # Pydantic models, paths, ConfigManager, vocabulary store
    ├── secrets/           # keyring wrapper
    ├── logging/           # setup + RingBufferHandler
    ├── ipc/               # NDJSON command/event servers + client
    ├── audio/             # capture session, devices, resample, metering
    ├── core/              # daemon, dictation, postprocess, voice commands, transcribe
    ├── providers/         # STT interface, capabilities, manager, Groq, Deepgram
    ├── hotkeys/           # HotkeyManager, bindings, pynput backend, focus capture
    ├── inject/            # TextInjector, Windows clipboard-paste injection
    ├── indicator/         # CaptureIndicator, NoOp, Windows tkinter overlay
    ├── daemon/            # Background spawn helpers
    └── tui/               # Textual client (dashboard, settings, onboarding)
```

## 6. Conventions

- **Python:** target 3.12, type hints everywhere, **`ruff`** for lint/format.
- **Async:** the daemon and TUI are async-first (Textual is async); keep the
  audio/STT pipeline non-blocking.
- **Comments:** explain *why*, not *what*. No narration comments.
- **Secrets:** never commit API keys; never log them. Use the keyring.
- **Cross-platform:** Windows, macOS, and Linux are all in scope long-term, but
  **Windows is the primary target** for the core loop first. Always isolate
  platform-specific code (hotkeys, injection, popup) behind interfaces so other
  platforms slot in later without touching the core.

## 8. Contribution rubric

Adapted from hermes-agent. Use when reviewing PRs or planning work.

### What we want

- **Fix real bugs** with reproduction on current `main` and line-level account of the fix.
- **Expand at the edges** — new STT providers, platform adapters (hotkeys, inject,
  indicator), TUI improvements — behind existing interfaces, not by growing the
  daemon core loop.
- **Daemon authority preserved** — TUI/CLI observe and command over IPC; config and
  keys flow through the daemon.
- **Behavior-contract tests** — assert invariants, not snapshot literals.
- **Cross-platform discipline** — fix portable first; gate only when OS-bound.

### What we don't want

- **Secrets in config files** — keyring only for API keys.
- **Unbounded PyPI deps** — use `>=floor,<next_major`.
- **Post-STT vocabulary replacement** — STT hints only (`sybl config vocab` terms).
- **TUI owning state** — no config drift between TUI and daemon.
- **Speculative abstractions** with no consumer.

### Footprint ladder (new capability)

1. Extend existing code
2. CLI command + docs
3. Gated optional module (loads when configured)
4. Provider/platform adapter behind interface
5. Core loop change (last resort)

### Verify premise before fixing

Read intent in git history and existing design. A limitation may be deliberate isolation,
not a gap.

## 7. Self-Maintenance Protocol (READ THIS, AGENT)

`AGENTS.md` is the project's living memory. **You are responsible for keeping it
accurate.** After any meaningful change, update the relevant sections in the
same task — do not defer it.

Update `AGENTS.md` whenever you:

- Change the mission, scope, or product behavior → update §1/§2.
- Advance the project's phase or status → update §3 (and `docs/ROADMAP.md`).
- Make or reverse a technical/architecture decision → append to §4.
- Add, move, or remove top-level files/directories → update §5.
- Establish or change a convention → update §6.

Rules:

1. **Bump `Last updated`** at the top whenever you edit this file.
2. **Append, don't erase** decisions in §4 — if a decision changes, add a new
   row/note explaining the change rather than deleting the old one.
3. **Keep it concise.** This is a map, not a manual. Link out to `docs/` for
   depth.
4. **If reality and this file disagree, this file is wrong — fix it.**
5. When you finish a unit of work, ask yourself: *"Did anything here go stale?"*
   If yes, update it before ending your turn.

## Cursor Cloud specific instructions

The cloud VM is **headless Linux**; sybl is **Windows-first**. The startup update
script runs `uv sync` (deps + dev group). System packages (`portaudio19-dev`,
`xvfb`, `python3-dev`) and `uv` are already baked into the snapshot — `uv` is on
`PATH`. `python3-dev` is required because `pynput`'s transitive `evdev` builds a C
extension needing `Python.h`.

- **Lint / test:** see `docs/DEVELOPMENT.md`. Run the suite with
  `python3 scripts/run_tests.py` (this VM exposes `python3`, not `python`). It runs
  ruff + `pytest -m "not integration"` under `xvfb-run`.
- **Known headless test failure:** `tests/test_hotkeys.py::test_emit_posts_to_async_handler`
  fails here with `Xlib.error.ConnectionClosedError` during pynput's X-RECORD
  listener teardown. It is a cumulative Xvfb/pynput teardown race across multiple
  listener start/stop cycles — it passes in isolation and is green on GitHub CI
  (169 passed). Not a code defect. For a fully green local run, deselect it:
  `--deselect tests/test_hotkeys.py::test_emit_posts_to_async_handler`.
- **The daemon cannot run on Linux.** `sybl start` (and `SyblDaemon`) eagerly build
  the Windows-only `TextInjector`, so they raise `NotImplementedError: Text injection
  is Windows-only in Phase 5`. Hotkeys/injection/indicator are Windows-only by design.
- **No mic, no GUI, no STT keys headless.** `sybl audio devices` finds none and live
  `sybl transcribe` / real STT need a BYOK provider key (Groq/Deepgram) + a mic.
  What *does* run headless: `sybl doctor`, `sybl config`, and the core text path
  (`sybl.core.postprocess.process_text` + `sybl.core.voice_commands.apply_voice_commands`),
  which is the speech→typed-text transformation every transcript flows through.
- Tests are hermetic via `SYBL_CONFIG_DIR` / `SYBL_STATE_DIR`; the Linux keyring uses
  `PYTHON_KEYRING_BACKEND=keyrings.alt.file.PlaintextKeyring` (set by `run_tests.py`).
