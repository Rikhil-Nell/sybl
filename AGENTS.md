# AGENTS.md

> Living source of truth for the Navi project. Read this first. Keep it current.
> Last updated: 2026-06-28 (Phase 7 complete)

---

## 1. Mission

**Navi is an open-source, bring-your-own-key (BYOK) voice dictation tool.**

Put your cursor anywhere, hit a global shortcut, speak/ramble into a lightweight
popup, and Navi transcribes it fast and types it in for you — wherever you were
about to type. It is the open-source answer to closed tools like Wispr Flow.

The guiding principles:

- **BYOK, provider-agnostic.** Users plug in whatever speech-to-text (STT)
  credits they already have — Deepgram, AssemblyAI, Gladia, Groq (Whisper
  large-v3), etc. No vendor lock-in, no Navi-hosted backend, no subscription.
- **Local-first & private.** Audio goes straight from the user's machine to the
  STT provider of their choice. Navi keeps no telemetry and stores nothing it
  doesn't have to.
- **Fast & invisible.** Dictation should feel instant and stay out of the way.
- **TUI, daemon-based.** Navi runs as a background daemon. All of its UI is a
  terminal UI (TUI): live logs, status, history, and config — nothing more.

## 2. What Navi Does (Product Spec)

- **Global activation.** A system-wide shortcut works regardless of focused app.
- **Two interaction modes:**
  - **Push-to-talk (PTT):** hold the shortcut, speak, release to finish.
  - **Toggle / constant recording:** a double-press of the shortcut starts
    continuous recording; press again to stop.
- **Popup capture surface.** When activated, a small indicator/popup appears so
  the user knows Navi is listening. *(Exact rendering approach is an open
  research item — see `docs/ROADMAP.md`.)*
- **BYOK transcription.** Audio is streamed/sent to the user's selected provider
  and transcribed quickly.
- **Text injection.** The transcript is inserted at the current cursor location
  in whatever app had focus when activation happened.
- **TUI surface.** A Textual-based TUI shows live logs, current state, and a
  scrollback history of recent transcriptions for reference.

## 3. Current State

> Update this section every time the project's reality changes.

- **Phase:** Phase 7 complete — daemon IPC + Textual TUI attach; Phase 8 (popup) is next.
- **Code:** `navi/audio/` implements `AudioCaptureSession` (sounddevice callback →
  asyncio queue, 16 kHz mono int16, resampling, dBFS peak metering, debug WAV save).
  `navi/providers/` implements streaming-first STT interface, `ProviderCapabilities`,
  `resolve_provider` session-start selection, `GroqProvider` (batch), and
  `DeepgramProvider` (WebSocket streaming + REST batch via official SDK).
  `navi/hotkeys/` implements `HotkeyManager`, binding parser, Windows `pynput` PTT
  backend, and focus capture at activation. `navi/inject/` implements `TextInjector`,
  Windows clipboard-paste injection with focus restore and clipboard restoration.
  `navi/core/` has `StateMachine`, `DictationController`, `NaviDaemon`, post-processing,
  `TranscriptHistory`, `EventBus`, and transcribe pipeline. `navi/ipc/` implements
  NDJSON command/event TCP servers and client. `navi/tui/` is a Textual app (logs,
  status, history, settings, BYOK onboarding). CLI: `navi start`, `navi stop`,
  `navi status`, `navi tui`, `navi config`, `navi doctor`, `navi audio`, `navi transcribe`,
  `navi hotkey test`.
- **Stack pinned:** `typer`, `pydantic`, `platformdirs`, `keyring`, `tomli-w`,
  `sounddevice`, `numpy`, `soundfile`, `soxr`, `groq`, `tenacity`, `deepgram-sdk`,
  `pynput`, `textual`; dev: `ruff`, `pytest`, `pytest-asyncio`.
- **Primary platform:** Windows first (dev machine). Code stays cross-platform
  behind interfaces, but the core loop is proven on Windows before expanding.
- **Open questions:** popup rendering mechanism; per-platform text-injection
  edge cases (Wayland especially); how aggressive default post-processing should
  be.

## 4. Architecture & Tech Decisions

> A decision log. Append new decisions; don't silently rewrite history.

| Area | Decision | Rationale |
|------|----------|-----------|
| Language | Python 3.12 | Already scaffolded; first-class STT SDKs; great TUI ecosystem. |
| Packaging / env | `uv` + `pyproject.toml` | Already in place; fast, reproducible. |
| TUI framework | Textual (pinned) | Modern, async, rich rendering for logs/history; `navi tui` attaches over IPC. |
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
| Secrets | OS keyring via `navi.secrets` | Keep API keys out of plaintext config; `navi config set-key`. |
| CLI | Typer subcommands | `start`, `stop`, `status`, `tui`, `config`, `doctor`, `audio`, `transcribe`, `hotkey`. |
| Logging | File + console + ring buffer | `navi.logging.setup_logging`; ring buffer for future TUI tail. |
| Phase 4 hotkeys | **PTT-first** via `pynput` behind `HotkeyManager`; focus captured at **activation press** | Reliability anchor before toggle mode; HWND stored for Phase 5 injection; Windows-only MVP. |
| Phase 5 injection | **Clipboard set + simulated Ctrl+V** via `SendInput` (ctypes); restore prior clipboard; focus restore with thread attach | Primary strategy on Windows; avoids pynput paste deadlock with hotkey listener; no new deps. |
| Phase 5.5 post-processing | **Rule-based pipeline** (`PostProcessConfig` + ordered passes) between STT and inject | Whitespace, filler trim, capitalize on by default; auto-punctuation off; Phase 9 expands without restructuring. |
| Phase 6 IPC | **TCP localhost NDJSON** — separate command + event ports; `daemon.json` + PID lock | Cross-platform; asyncio-native; TUI/CLI attach without shared memory. |
| Phase 7 TUI | **Textual dashboard** — logs, status, history, settings, BYOK onboarding | All config/key writes routed through daemon IPC; keyboard-driven MVP. |

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
                           │ IPC (logs / state / history)
                  +--------+--------+
                  |   TUI Client    |
                  | (Textual app)   |
                  +-----------------+
```

## 5. Project Structure

> Keep this in sync with the real tree as it grows.

```
Navi/
├── AGENTS.md
├── README.md
├── docs/
│   ├── ROADMAP.md
│   └── RESEARCH-NOTES.md   # recovered planning + research-agent rationale
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
│   ├── test_history.py
│   ├── test_hotkeys.py
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
│   └── test_tui_client.py
└── navi/
    ├── __init__.py
    ├── __main__.py
    ├── cli/               # start, stop, status, tui, config, doctor, audio, transcribe, hotkey
    ├── config/            # Pydantic models, paths, ConfigManager
    ├── secrets/           # keyring wrapper
    ├── logging/           # setup + RingBufferHandler
    ├── ipc/               # NDJSON command/event servers + client
    ├── audio/             # capture session, devices, resample, metering
    ├── core/              # daemon, state machine, dictation, history, events, transcribe
    ├── providers/         # STT interface, capabilities, manager, Groq, Deepgram
    ├── hotkeys/           # HotkeyManager, bindings, pynput backend, focus capture
    ├── inject/            # TextInjector, Windows clipboard-paste injection
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
