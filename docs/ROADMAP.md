# Navi — Roadmap

> Ordered plan of execution. Phases are sequential-ish; later phases assume the
> earlier ones exist. There are **no time estimates** here on purpose — the order
> is the plan. Items inside a phase are roughly ordered too.
>
> See `AGENTS.md` for the mission and the high-level architecture this builds.

> **Primary platform: Windows first.** The core loop (hotkeys → audio →
> transcribe → cleanup → inject) is proven on Windows before macOS/Linux. All
> platform-specific code stays behind interfaces so other OSes slot in later
> without touching the core. This avoids burning early effort on the hardest
> cross-platform details (hotkeys, injection, popup) on three OSes at once.

> **Two concerns are first-class from early on, not bolted on late:** the
> **state machine** (idle → listening → processing → injecting) and the
> **post-processing pipeline** (provider text → cleanup → injection). They sit at
> the center of the UX and the core text path.

## Legend

- `[ ]` not started · `[~]` in progress · `[x]` done
- **★** = milestone you can actually feel/use ("demo-able").

---

## Phase 0 — Foundations & Project Skeleton

Goal: turn the hello-world stub into a real, runnable project with config,
logging, and the seams every later phase plugs into.

- [x] Decide and pin tooling: `ruff` (lint/format), `pytest` (tests), typing.
- [x] Define package layout, e.g. `navi/` with `cli`, `core`, `audio`,
      `providers`, `inject`, `hotkeys`, `tui`, `config` modules.
- [x] CLI entrypoint (replace `main.py`): `navi start`, `navi tui`,
      `navi config`, `navi doctor`.
- [x] Config system: a TOML config file (e.g. `~/.config/navi/config.toml`) +
      sane defaults + **Pydantic** schema validation.
- [x] Secure secret storage via OS keyring for provider API keys (BYOK).
- [x] Structured logging that the TUI can later tail (log to file + in-memory
      ring buffer).
- [x] `navi doctor`: environment/dependency/permission self-check.

## Phase 1 — Audio Capture Pipeline ★

Goal: reliably capture microphone audio in the format STT providers want.

> **Architecture:** sounddevice **callback thread** → `asyncio.Queue` → daemon
> event loop → provider layer. The callback only copies PCM into the queue —
> no heavy work in the callback.

- [x] Microphone capture with `sounddevice` (`InputStream` callback mode as the
      primary path; blocking `rec()` acceptable only for simple batch capture).
- [x] **Fixed format:** `samplerate=16000`, `channels=1`, `dtype=int16`; resample
      in-pipeline when the device opens at 48 kHz.
- [x] Device selection from config by **index and/or name** with fallback when
      indices change across reboots.
- [x] Stream PCM into a buffer/queue; support both "record until stop" and chunked
      streaming for real-time providers.
- [x] Audio session lifecycle: start, stop, cancel; context managers +
      explicit `stream.stop()` / `stream.close()` to avoid device leaks.
- [x] **Level metering:** RMS for the TUI/popup indicator; plan VAD upgrade
      (`webrtcvad` or `silero-vad`) later — RMS alone is not enough to trim
      silence reliably.
- [x] Handle stream errors gracefully (Bluetooth hot-unplug, permission loss).
- [x] Save-last-recording debug option via **`soundfile`** (not `scipy.io.wavfile`).

## Phase 2 — STT Provider Abstraction (streaming-first) + First Signal ★

Goal: a clean, **streaming-first** pluggable interface, with text coming back
end to end. Designing for streaming now avoids reworking the interface later when
batch turns out to be the easy/degenerate case.

- [x] Define the `Provider` interface **streaming-first**, **async from day one**:
      `async def transcribe(audio: bytes | AsyncIterable[bytes]) ->
      AsyncGenerator[TranscriptionResult, None]` where `TranscriptionResult`
      carries `text`, `is_final`, and optional `confidence`. Batch Groq is the
      degenerate "buffer-all-then-send-once" case.
- [x] Sketch the **state machine module** now (idle → listening → processing →
      injecting, + cancelled/error) even before the daemon wraps it — the rest of
      the pipeline plugs into it.
- [x] Provider registry; per-provider key from keyring
      (`keyring.get_password("navi", "groq_api_key")`, etc.).
- [x] **First signal — Groq (Whisper), batch:** fastest path to "record
      → get text in the terminal", implemented behind the streaming interface.
      Model id configurable (`whisper-large-v3` vs `whisper-large-v3-turbo`;
      default turbo for dictation speed).
- [x] Custom STT exception hierarchy + **`tenacity`** retries for transient
      failures (rate limits, network blips); fatal errors (bad key, bad format)
      fail fast.
- [x] **Milestone:** record audio → transcribe via Groq → print clean text +
      basic metadata (provider, duration) in the terminal.

## Phase 3 — Reference Streaming Provider + the Rest

Goal: real-time transcription via the reference provider, then fill the BYOK
matrix.

- [ ] **Deepgram (streaming websocket) as the reference implementation** — manage
      connection lifecycle, ~20–100 ms audio chunks, partial vs final results,
      and reconnection on disconnect.
- [ ] AssemblyAI (streaming).
- [ ] Gladia (lower priority unless multilingual demand).
- [ ] **`ProviderCapabilities`** metadata per provider (streaming, partials,
      languages, punctuation, diarization, max duration, etc.).
- [ ] **`ProviderManager`** layer: load keys, check capabilities, honor
      `preferred_stt` + `fallback_order` from config — fallback only at **session
      start**, not mid-stream; log which provider actually ran.

## Phase 4 — Global Hotkeys + Interaction Modes ★

Goal: activate Navi from anywhere. **PTT is the reliability anchor;** toggle mode
is secondary and harder to get right.

> `pynput` is fine for an MVP on Windows; abstract it behind `HotkeyManager`
> from day one. Long-term target for production polish: a small **native helper**
> (Rust `global-hotkey` crate is the usual choice). Do **not** use the `keyboard`
> library (Windows security warnings, macOS root requirements).

- [ ] `HotkeyManager` interface + `pynput` implementation (configurable binding).
- [ ] **Push-to-talk (primary):** hold to record, release to finish.
- [ ] **Double-press toggle (secondary):** start constant recording; press again
      to stop — ship after PTT is solid; debounce/timing will need tuning.
- [ ] Cancel gesture (e.g. Esc) to discard the in-flight capture.
- [ ] Capture focused window/target at **hotkey press**, not at injection time.
- [ ] Windows implementation first; macOS (Accessibility permissions) and Linux
      (X11 vs Wayland limits) later behind the same interface.
- [ ] **Escape hatch:** native hotkey helper if `pynput` misses events under load.

## Phase 5 — Text Injection ★

Goal: put the transcript where the user was going to type.

> **Reality check:** Wispr Flow uses **native per-OS injection** (macOS
> `CGEvent`/Accessibility, Windows `SendInput`, clipboard+paste as fallback).
> Pure Python can get to "very good for open source" via clipboard paste; matching
> commercial polish in every app eventually needs a native helper. Be transparent
> in docs, especially for macOS and Wayland.

- [ ] `TextInjector` interface; capture focused target at **activation** time.
- [ ] **Primary — clipboard set + simulated paste (Ctrl/Cmd+V)**, restoring the
      user's previous clipboard afterward. Ship this first; it is the milestone.
- [ ] **Secondary / experimental — direct synthetic keystrokes** for edge cases
      where paste is undesirable.
- [ ] Windows first (`SendInput` or paste simulation); macOS Accessibility and
      Linux X11 later; document Wayland limitations honestly.
- [ ] Config to choose strategy; sensible Windows default = paste.
- [ ] **Milestone:** hotkey → speak → polished text appears in the previously
      focused app via clipboard paste. Keystroke injection is a later opt-in.

## Phase 5.5 — Minimal Post-Processing Seam (in the core path) ★

Goal: establish the cleanup step *now*, since it lives in the core path (provider
text → cleanup → injection) and is much of the perceived quality. Keep it small;
Phase 9 expands it.

- [ ] A post-processing stage that runs after the provider returns and before
      injection, wired through the state machine's `processing` state.
- [ ] Lightweight rule-based cleanup: basic punctuation/capitalization, trim
      filler words ("um", "uh"), collapse obvious rambling artifacts.
- [ ] Make it a pluggable pipeline (ordered passes) so LLM/format passes and
      custom vocabulary drop in later without restructuring.

## Phase 6 — Daemon + IPC

Goal: make Navi a always-on background service the TUI can attach to.

- [ ] Daemon process that owns hotkeys, audio, providers, and injection.
- [ ] State machine: `idle → listening → transcribing → injecting → idle`
      (+ `cancelled`, `error`).
- [ ] Local IPC: a simple **command/response** channel + a separate **log/event
      stream** (don't try to share complex objects across processes). Daemon
      keeps a **ring buffer** for logs & recent history so the TUI reconnects
      cleanly and memory stays predictable.
- [ ] **Config flows through the daemon** so changes persist and take effect
      immediately — TUI and daemon never drift out of sync.
- [ ] Start/stop/status management; single-instance guard; graceful shutdown
      (users start/stop the daemon constantly during dev).
- [ ] Auto-start integration docs (systemd user service / launchd / Windows
      startup) — optional opt-in.

## Phase 7 — TUI ★

Goal: the only UI Navi has — terminal-native, for logs and reference.

- [ ] Textual app that connects to the daemon over IPC.
- [ ] Live log view (tails the daemon's ring buffer).
- [ ] Status panel: current state, active provider, mic, current binding.
- [ ] Transcription history: scrollback of recent transcripts to copy/refer to.
- [ ] In-TUI config screens: provider selection, keys, hotkeys, device — all
      writes routed through the daemon (no direct file edits from the TUI).
- [ ] First-run **BYOK onboarding**: a clear, guided key-setup flow (this is the
      make-or-break moment for a BYOK tool).
- [ ] Keyboard-driven everything; no mouse required.

## Phase 8 — The "Popup" Capture Indicator

Goal: a small on-screen cue that Navi is listening near the cursor.

> This is the most platform-dependent piece and is intentionally late: the
> product is fully usable without it. Research/spike before committing.

- [ ] Spike the options and pick per-platform approaches:
  - Tiny always-on-top borderless window (e.g. a minimal native/Qt/GTK overlay).
  - OS-native overlay APIs.
  - Tray/menubar icon state change as a low-effort fallback.
- [ ] Live mic level / waveform in the indicator.
- [ ] Position near the text cursor / active window where feasible.
- [ ] Graceful degradation: if no overlay is possible, fall back to a sound or
      tray cue.

## Phase 9 — Dictation Quality & Power Features

Goal: make the output genuinely good to use day to day. **Expands the Phase 5.5
seam** rather than starting fresh.

- [ ] Deepen rule-based cleanup beyond the minimal pass.
- [ ] Custom vocabulary / replacements dictionary (names, jargon, snippets) —
      cheap to add, high-leverage, gives users immediate control.
- [ ] Optional LLM "format pass" (also BYOK) for tone/cleanup.
- [ ] Voice commands (e.g. "new line", "scratch that").
- [ ] Per-app profiles / language selection.

## Phase 10 — Packaging, Docs & Open-Source Release

Goal: ship it so others can install and contribute.

- [ ] README with quickstart + the BYOK provider setup guide.
- [ ] Distribution: PyPI (`uv`/`pipx` install) and platform notes.
- [ ] Permissions guide (mic + accessibility/input permissions per OS).
- [ ] LICENSE (OSI-approved), CONTRIBUTING, issue/PR templates.
- [ ] CI: lint, type-check, tests across platforms.
- [ ] Versioned releases.

---

## Critical path (the shortest line to "it works")

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 4  →  Phase 5  →  Phase 5.5
skeleton    audio       1 signal     hotkeys    injection   min. cleanup
                        (Groq,        (PTT/      (clipboard
                        streaming     toggle)     paste)
                        interface)
```

Proven on **Windows first**. After this line, Navi already does the core job from
the keyboard with usable output. Phases 3, 6, 7, 8+ make it robust, always-on,
observable, multi-provider, and pleasant.

## Open questions to resolve along the way

- Popup rendering: which mechanism per platform, and how to position it near the
  cursor (Phase 8 spike).
- Streaming vs batch as the **default** UX (latency vs accuracy vs cost) — the
  interface supports both; which is the default ships as a decision.
- Wayland text injection limitations and the best fallback (post-Windows).
- How aggressive the default post-processing should be (Phase 5.5 / Phase 9).
- When to invest in a **native helper** for hotkeys and/or injection (after
  `pynput` + paste plateau on Windows).
- Local/offline STT (e.g. faster-whisper): out of scope for BYOK v1; capability
  flags should leave room for it later without redesign.
