# sybl — Roadmap

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
- [x] Define package layout, e.g. `sybl/` with `cli`, `core`, `audio`,
      `providers`, `inject`, `hotkeys`, `tui`, `config` modules.
- [x] CLI entrypoint (replace `main.py`): `sybl start`, `sybl tui`,
      `sybl config`, `sybl doctor`.
- [x] Config system: a TOML config file (e.g. `~/.config/sybl/config.toml`) +
      sane defaults + **Pydantic** schema validation.
- [x] Secure secret storage via OS keyring for provider API keys (BYOK).
- [x] Structured logging that the TUI can later tail (log to file + in-memory
      ring buffer).
- [x] `sybl doctor`: environment/dependency/permission self-check.

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
      (`keyring.get_password("sybl", "groq_api_key")`, etc.).
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

- [x] **Deepgram (streaming websocket) as the reference implementation** — manage
      connection lifecycle, ~20–100 ms audio chunks, partial vs final results,
      and reconnection on disconnect.
- [ ] AssemblyAI (streaming).
- [ ] Gladia (lower priority unless multilingual demand).
- [x] **`ProviderCapabilities`** metadata per provider (streaming, partials,
      languages, punctuation, diarization, max duration, etc.).
- [x] **`ProviderManager`** layer: load keys, check capabilities, honor
      `preferred_stt` + `fallback_order` from config — fallback only at **session
      start**, not mid-stream; log which provider actually ran.

## Phase 4 — Global Hotkeys + Interaction Modes ★

Goal: activate sybl from anywhere. **PTT is the reliability anchor;** toggle mode
is secondary and harder to get right.

> `pynput` is fine for an MVP on Windows; abstract it behind `HotkeyManager`
> from day one. Long-term target for production polish: a small **native helper**
> (Rust `global-hotkey` crate is the usual choice). Do **not** use the `keyboard`
> library (Windows security warnings, macOS root requirements).

- [x] `HotkeyManager` interface + `pynput` implementation (configurable binding).
- [x] **Push-to-talk (primary):** hold to record, release to finish.
- [ ] **Double-press toggle (secondary):** start constant recording; press again
      to stop — ship after PTT is solid; debounce/timing will need tuning.
- [x] Cancel gesture (e.g. Esc) to discard the in-flight capture.
- [x] Capture focused window/target at **hotkey press**, not at injection time.
- [x] Windows implementation first; macOS (Accessibility permissions) and Linux
      (X11 vs Wayland limits) later behind the same interface.
- [ ] **Escape hatch:** native hotkey helper if `pynput` misses events under load.

## Phase 5 — Text Injection ★

Goal: put the transcript where the user was going to type.

> **Reality check:** Wispr Flow uses **native per-OS injection** (macOS
> `CGEvent`/Accessibility, Windows `SendInput`, clipboard+paste as fallback).
> Pure Python can get to "very good for open source" via clipboard paste; matching
> commercial polish in every app eventually needs a native helper. Be transparent
> in docs, especially for macOS and Wayland.

- [x] `TextInjector` interface; capture focused target at **activation** time.
- [x] **Primary — clipboard set + simulated paste (Ctrl/Cmd+V)**, restoring the
      user's previous clipboard afterward. Ship this first; it is the milestone.
- [ ] **Secondary / experimental — direct synthetic keystrokes** for edge cases
      where paste is undesirable.
- [x] Windows first (`SendInput` or paste simulation); macOS Accessibility and
      Linux X11 later; document Wayland limitations honestly.
- [x] Config to choose strategy; sensible Windows default = paste.
- [x] **Milestone:** hotkey → speak → polished text appears in the previously
      focused app via clipboard paste. Keystroke injection is a later opt-in.

## Phase 5.5 — Minimal Post-Processing Seam (in the core path) ★

Goal: establish the cleanup step *now*, since it lives in the core path (provider
text → cleanup → injection) and is much of the perceived quality. Keep it small;
Phase 9 expands it.

- [x] A post-processing stage that runs after the provider returns and before
      injection, wired through the state machine's `processing` state.
- [x] Lightweight rule-based cleanup: basic punctuation/capitalization, trim
      filler words ("um", "uh"), collapse obvious rambling artifacts.
- [x] Make it a pluggable pipeline (ordered passes) so LLM/format passes and
      custom vocabulary drop in later without restructuring.

## Phase 6 — Daemon + IPC

Goal: make sybl a always-on background service the TUI can attach to.

- [x] Daemon process that owns hotkeys, audio, providers, and injection.
- [x] State machine: `idle → listening → processing → injecting → idle`
      (+ `cancelled`, `error`) — exposed over IPC events.
- [x] Local IPC: a simple **command/response** channel + a separate **log/event
      stream** (don't try to share complex objects across processes). Daemon
      keeps a **ring buffer** for logs & recent history so the TUI reconnects
      cleanly and memory stays predictable.
- [x] **Config flows through the daemon** so changes persist and take effect
      immediately — TUI and daemon never drift out of sync.
- [x] Start/stop/status management; single-instance guard; graceful shutdown
      (users start/stop the daemon constantly during dev).
- [x] Auto-start integration docs (systemd user service / launchd / Windows
      startup) — optional opt-in; see [`docs/DAEMON.md`](DAEMON.md).

## Phase 7 — TUI ★

Goal: the only UI sybl has — terminal-native, for logs and reference.

- [x] Textual app that connects to the daemon over IPC.
- [x] Live log view (tails the daemon's ring buffer).
- [x] Status panel: current state, active provider, mic, current binding.
- [x] Transcription history: scrollback of recent transcripts to copy/refer to.
- [x] In-TUI config screens: provider selection, keys, postprocess/inject toggles —
      all writes routed through the daemon (hotkey rebinding deferred).
- [x] First-run **BYOK onboarding**: a clear, guided key-setup flow (this is the
      make-or-break moment for a BYOK tool).
- [x] Keyboard-driven everything; no mouse required.

## Phase 8 — The "Popup" Capture Indicator

Goal: a small on-screen cue that sybl is listening near the cursor.

> Windows MVP shipped; macOS/Linux overlays deferred behind `CaptureIndicator`.

- [x] Spike the options and pick per-platform approaches — see [`docs/POPUP-SPIKE.md`](POPUP-SPIKE.md).
- [x] Live mic level in the indicator (RMS level bar; waveform polish deferred).
- [x] Position near the text cursor on show (`GetCursorPos` + config offset).
- [x] Graceful degradation: overlay creation failure logs once and falls back to
      no-op; dictation unaffected. *(Sound/tray cue deferred.)*

## Phase 9 — Dictation Quality & Power Features

Goal: make the output genuinely good to use day to day. **Expands the Phase 5.5
seam** rather than starting fresh.

- [x] Deepen rule-based cleanup beyond the minimal pass (quote/dash normalize,
      punct spacing, optional repeated-word collapse).
- [x] Custom vocabulary **STT hints** (names, jargon) — Deepgram keyterms + Groq
      prompt; `sybl config vocab` CLI. *(Post-STT replacement dictionary deferred;
      future LLM pass reuses the same term list.)*
- [ ] Optional LLM "format pass" (also BYOK) for tone/cleanup — deferred.
- [x] Voice commands on the final transcript (`new line`, `period`, `comma`).
      *(Scratch-that cancel removed — use Esc; transcripts stay in history.)*
- [ ] Per-app profiles / language selection — out of scope for now (English-first).

## Phase 10 — Packaging, Docs & Open-Source Release

Goal: ship it so others can install and contribute.

- [x] README with quickstart + the BYOK provider setup guide.
- [x] Distribution: PyPI (`uv`/`pipx` install) and platform notes.
- [x] Permissions guide (mic + accessibility/input permissions per OS).
- [x] LICENSE (OSI-approved), CONTRIBUTING, issue/PR templates.
- [x] CI: lint, type-check, tests across platforms.
- [x] Versioned releases (v0.1.0).

---

## Release plan (post v0.1.0)

Phases 0–10 are the historical build plan. **Going forward, work ships in
semver releases.** Patch releases (0.1.x) are incremental — deferred items from
the phase plan, hygiene, and stability. Minor releases (0.2.0+) carry new
providers, platform ports, and larger features.

| Release | Theme |
|---------|--------|
| **v0.1.0** | First public release (Phases 0–10) |
| **v0.1.1** | Incremental — finish deferred v0.1.0 gaps + project hygiene |
| **v0.1.2** | Heavy TUI overhaul — terminal UX is the product surface |
| **v0.2.0** | Next milestone — new STT providers, macOS/Linux backends, native helpers |

---

## v0.1.1 — Incremental patch ★

Goal: close the small deferred items from the v0.1.0 ship, harden the project
for contributors, and fix real-world rough edges — **no large new subsystems**.

### Deferred from v0.1.0 (ship now)

- [x] **Double-press toggle mode** — constant recording; press again to stop
      (Phase 4; debounce/timing tuning; PTT remains default).
- [x] **In-TUI hotkey rebinding** — change the PTT/toggle binding from Settings
      without editing `config.toml` by hand (Phase 7 deferral).
- [x] **Indicator sound cue** — optional short audio on listen start/stop
      (`[indicator]` config; graceful no-op when audio unavailable).

### Hygiene & contributor surface (Hermes-shaped)

- [x] **Dependency upper bounds** — `>=floor,<next_major` on all PyPI deps in
      `pyproject.toml`; document policy in `CONTRIBUTING.md`.
- [x] **`scripts/run_tests.sh`** — hermetic test runner (isolated config home,
      TZ/LANG parity with CI); prefer over raw `pytest` in docs.
- [x] **AGENTS.md contribution rubric** — want/don't-want, footprint ladder,
      verify-premise-before-fix (adapted from hermes-agent).
- [x] **Cross-platform CI grep** — workflow or lint pass flagging Unix-only
      patterns in diffs (`fcntl`, hardcoded `/tmp`, `os.kill(pid, 0)`, etc.).

### Quality & diagnostics

- [x] **`sybl doctor` depth** — `sybl doctor --live` for reachability ping, mic
      capture smoke, inject self-test (actionable remediation lines).
- [x] **Stability pass** — TUI IPC error visibility, reconnect banner, IPC
      connect timeouts, daemon hotkey reload ordering.
- [x] **Docs touch-up** — permissions threat model (keyring vs config), install
      time expectations, toggle-mode usage.

### Explicitly rejected for v0.1.1

- **Post-STT vocabulary replacement** — STT hints only (`sybl config vocab` terms);
  no downstream find-and-replace map.

### Explicitly out of scope for v0.1.1

AssemblyAI/Gladia providers, macOS/Linux hotkey/inject/indicator backends,
native hotkey helper, LLM format pass, synthetic keystroke injection,
per-app profiles, VAD (`webrtcvad` / `silero-vad`), waveform indicator polish,
tray-icon fallback — these stay on the backlog for v0.2.0+ unless a critical
fix forces an exception.

---

## v0.1.2 — Heavy TUI overhaul ★

Goal: the TUI is sybl's only UI — make it feel as polished as the dictation
loop. Inspired by hermes-agent's terminal UX discipline: **instant first frame,
non-blocking attach, modal overlays, one backend / thin client.**

> v0.1.2 is a **UI release**, not a feature dump. New providers and OS ports
> wait for v0.2.0.

### Architecture (before pixels)

- [x] **Thin-client contract** — document and enforce: TUI never owns config,
      keys, or state; all writes go through daemon IPC; widgets are pure views.
- [x] **Event-driven refresh** — replace polling-heavy paths with IPC event
      subscriptions where possible (state, level, history append, log tail).
- [x] **Instant attach** — dashboard shell renders on first frame; data fills in
      progressively (status → logs → history) so `sybl tui` never feels frozen.
- [ ] **Central UI action registry** — one map of keybindings / slash-style
      commands shared by dashboard, settings modals, and onboarding (no drift).

### Layout & navigation

- [x] **Dashboard redesign** — Sibyl Royal zone layout: chrome → context →
      session|transcripts → logs → footer (see `docs/DESIGN-v0.1.2.md`).
- [x] **Modal overlays** — settings and help as stacked modals; Esc dismisses
      without losing dashboard context.
- [x] **Settings config-editor** — sidebar section rail + per-section heading,
      description, labeled forms, and sized sound-cue rows (no more haphazard
      layout / oversized sidebar).
- [x] **Raw config edit** — open `config.toml` in `$EDITOR` from the dashboard
      (`e`) or `sybl config edit`; both reload the running daemon.
- [ ] **Onboarding wizard** — step-by-step BYOK flow (provider → key → test
      mic → first dictation) with progress indicator; skippable on return visits.
- [x] **History UX** — client-side filter, selectable rows, `y` copy; keyboard
      navigation via ListView (↑/↓).
- [ ] **Log UX** — level filter (INFO/WARN/ERROR), auto-scroll toggle, dim
      timestamps; optional source/component tags if daemon emits them.

### Live feedback

- [x] **In-TUI mic meter** — RMS level bar while daemon is in `LISTENING`;
      driven by IPC `level` events.
- [x] **State machine visibility** — idle / listening / processing / injecting
      shown prominently with provider name and session timing.
- [x] **Connection health** — daemon attach/reconnect indicator; graceful
      offline mode when IPC drops (retry banner, read-only history).

### Polish

- [x] **Textual design system** — `sybl/tui/theme/sibyl_royal.tcss` (panels,
      borders, accent, status colors); dark-first Sibyl Royal palette.
- [x] **Notification toasts** — config saved, key stored, copy succeeded, inject
      errors — non-blocking, consistent placement.
- [x] **Help overlay** — `?` shows keybindings and quick commands in a modal.
- [ ] **Screenshot / docs figures** — update README and getting-started with the
      new TUI layout.

### Testing

- [x] **TUI widget tests** — Textual pilot tests for dashboard zones, settings
      modal save → IPC mock, section nav, hotkey validation.
- [ ] **IPC integration tests** — event stream drives widget updates without a
      live daemon where feasible.

### Deferred to v0.2.0+ (even if tempting in UI work)

Ink/React second frontend, web dashboard, Electron app, skins marketplace,
mouse-required flows, per-app profile UI.

---

## v0.2.0 — Backlog preview (not scheduled)

Items deferred across Phases 3–9 and open questions — **not** part of 0.1.x:

- [ ] AssemblyAI streaming provider.
- [ ] Gladia provider (multilingual demand).
- [ ] macOS hotkeys (Accessibility) + injection + indicator backends.
- [ ] Linux X11 injection; honest Wayland documentation/fallback.
- [ ] Native hotkey helper (Rust `global-hotkey` escape hatch).
- [ ] Secondary synthetic keystroke injection strategy.
- [ ] Optional BYOK LLM format pass.
- [ ] VAD for silence trim (`webrtcvad` or `silero-vad`).
- [ ] Indicator: cursor-follow every frame, waveform, tray-icon fallback.
- [ ] Per-app profiles / language selection.
- [ ] Streaming vs batch as configurable default UX.
- [ ] Local/offline STT hook (capability flags only until implemented).

---

## Critical path (the shortest line to "it works")

```
Phase 0  →  Phase 1  →  Phase 2  →  Phase 4  →  Phase 5  →  Phase 5.5
skeleton    audio       1 signal     hotkeys    injection   min. cleanup
                        (Groq,        (PTT/      (clipboard
                        streaming     toggle)     paste)
                        interface)
```

Proven on **Windows first**. After this line, sybl already does the core job from
the keyboard with usable output. Phases 3, 6, 7, 8+ make it robust, always-on,
observable, multi-provider, and pleasant.

## Open questions (tracked in v0.2.0 backlog)

- Popup rendering on macOS/Linux — Windows tkinter MVP done.
- Streaming vs batch as the **default** UX (latency vs accuracy vs cost).
- Wayland text injection limitations and the best fallback.
- How aggressive the default post-processing should be.
- When to invest in a **native helper** for hotkeys and/or injection.
- Local/offline STT (e.g. faster-whisper): capability flags should leave room
  without redesign.
