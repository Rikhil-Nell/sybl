# Navi — Research & Planning Notes

> **Why this file exists:** A long planning session (2026-06-26, ~1:17–3:00 AM IST) in
> the Navi Cursor chat produced architecture decisions, research-agent cross-validation,
> and phased technical review. The **work landed in the repo** (`AGENTS.md`,
> `docs/ROADMAP.md`, Phase 0 code), but the **chat UI no longer shows that history**
> for the user — likely a Cursor display/persistence bug. This document recovers the
> reasoning so future sessions do not depend on chat scrollback.
>
> **Source transcript (Cursor internal):** chat id `3732d215-86c0-4ebd-afee-ff43dffdd3b5`

---

## Session timeline (what happened, in order)

| Step | What |
|------|------|
| 1 | User described Navi (open-source Wispr Flow, BYOK, global shortcut, popup TBD, PTT + double-press toggle, TUI daemon). Asked for self-updating `AGENTS.md`, a Cursor rule, and ordered roadmap (no time estimates). |
| 2 | Agent created `AGENTS.md`, `.cursor/rules/maintain-agents-md.mdc`, `docs/ROADMAP.md` (Phases 0–10). |
| 3 | User pasted **research agent cross-validation** (~2:40 AM) — daemon as SSOT, streaming-first, Windows depth-first, post-processing early, etc. |
| 4 | Agent updated `AGENTS.md` + `ROADMAP.md` (Phase 5.5, Windows-first, Deepgram reference / Groq first signal). |
| 5 | User pasted **detailed Phase 1–5 technical review** (sounddevice callback+queue, async STT interface, ProviderManager, pynput limits, Wispr native injection reality). |
| 6 | Agent folded that into `AGENTS.md` §4 and `ROADMAP.md` Phases 1–5; answered asyncio vs threading, Phase 4/5 ordering, Wispr comparison. |
| 7 | User asked to plan Phase 0; agent produced Phase 0 plan. |
| 8 | User approved implementation; **Phase 0 completed** — full `navi/` package, CLI, config, keyring, logging, tests. |
| 9 | User noticed missing chat history; agent explained distill-into-repo vs missing transcript doc. |

---

## 1. Research agent cross-validation (architecture)

**Thesis:** Build a tight core loop first (audio → clean text → inject). Everything else is layers.

### Adopted into the plan

| Theme | Decision |
|-------|----------|
| Daemon authority | Daemon owns mic, providers, state machine, injection, **config**. TUI is thin observe/command client. |
| IPC | Simple command/response + separate log/event stream; ring buffer in daemon. |
| Streaming-first STT | Design interface for streaming; batch (Groq) is degenerate "buffer all, send once". |
| Reference provider | **Deepgram** streaming = reference implementation; **Groq** batch = first end-to-end signal. |
| Primary platform | **Windows first** (user's dev machine). Interfaces stay cross-platform; prove core loop on one OS. |
| Injection | **Clipboard + paste primary**; synthetic keystrokes secondary/experimental. |
| Post-processing | **First-class early** — added **Phase 5.5** minimal cleanup seam on critical path. |
| State machine | Sketch in **Phase 2**, not only when daemon arrives (Phase 6). |
| Hotkeys | `pynput` MVP behind `HotkeyManager`; **native helper escape hatch** if reliability stalls. |
| Popup | Nice-to-have; tray/audio fallback until Phase 8 spike. |
| BYOK onboarding | First-run key setup in TUI phase — make-or-break for BYOK tools. |
| Breadth vs depth | Resist multi-OS + multi-provider + fancy overlay before core loop works on Windows. |

### Reconciliation (not blind agreement)

- **Groq-first vs Deepgram-first:** Both — Groq for fastest demo, Deepgram for honest streaming abstraction. No interface rework later.

### Where it lives now

- `AGENTS.md` §3–§4, §6
- `docs/ROADMAP.md` header notes, Phases 2–7, critical path

---

## 2. Phase 1–5 technical review (implementation detail)

### Phase 1 — Audio

| Item | Recommendation |
|------|----------------|
| Library | Keep `sounddevice` — good NumPy integration, callbacks, cross-platform. |
| Format | **16 kHz, mono, int16 PCM**; resample if device opens at 48 kHz. |
| Architecture | **Callback thread → `asyncio.Queue` → asyncio event loop** — never heavy work in callback. |
| Streaming | `InputStream` callback primary; blocking `rec()` only for simple batch. |
| Metering | RMS for UI now; **VAD later** (`webrtcvad` or `silero-vad`). |
| Debug | Save last recording with **`soundfile`**, not `scipy.io.wavfile`. |
| Devices | Config by index **and** name; fallback when indices change. |
| Lifecycle | Context managers + explicit `stop()` / `close()` — avoid device leaks. |
| Gotchas | macOS permissions, Bluetooth hot-unplug, permission loss. |

### Phase 2 — STT abstraction

| Item | Recommendation |
|------|----------------|
| Interface | **Async from day one** — `async def transcribe(audio: bytes \| AsyncIterable[bytes]) -> AsyncGenerator[TranscriptionResult, None]` with `text`, `is_final`, optional `confidence`. |
| First provider | Groq Whisper large-v3 batch behind streaming interface; configurable `whisper-large-v3` vs `turbo`. |
| Keys | `keyring.get_password("navi", "groq_api_key")` pattern per provider. |
| Errors | Custom hierarchy (`STTError`, `STTRateLimitError`, …) + **`tenacity`** for transient retries. |
| Config | **Pydantic** validation (adopted in Phase 0). |
| Milestone | Record → Groq → **clean text + metadata** in terminal. |

### Phase 3 — More providers

| Item | Recommendation |
|------|----------------|
| Priority | Deepgram streaming first, then AssemblyAI, Gladia lower unless multilingual demand. |
| Capabilities | `ProviderCapabilities` dataclass (streaming, partials, languages, punctuation, diarization, max duration, …). |
| Fallback | **`ProviderManager`** above providers; `preferred_stt` + `fallback_order` in config; fallback **only at session start**, not mid-stream; log which provider ran. |
| Deepgram | WebSocket lifecycle, 20–100 ms chunks, partial vs final, reconnection. |

### Phase 4 — Hotkeys

| Item | Recommendation |
|------|----------------|
| MVP | `pynput` behind `HotkeyManager` — **do not use `keyboard` library** (security/root issues). |
| Modes | **PTT primary** (reliability anchor); double-press toggle secondary, ship after PTT solid. |
| Long-term | Rust **`global-hotkey`** crate or small native helper. |
| Capture | Focused window at **hotkey press**, not injection time. |
| Platform pain | macOS Accessibility; Wayland global hotkey restrictions. |

### Phase 5 — Text injection

| Item | Recommendation |
|------|----------------|
| Primary | Clipboard set + simulated Ctrl/Cmd+V, restore prior clipboard. |
| Secondary | Synthetic keystrokes — experimental. |
| Wispr reality | Commercial tools use **native per-OS APIs** (macOS `CGEvent`/Accessibility, Windows `SendInput`); clipboard is fallback for them too. Pure Python caps at "very good OSS" without native helper eventually. |
| Docs | Be transparent about macOS and Wayland limitations. |

### Daemon concurrency (answered in session)

```
sounddevice callback thread  →  asyncio.Queue  →  asyncio event loop
                                                      ├─ state machine
                                                      ├─ STT (async generators / websockets)
                                                      ├─ post-processing
                                                      ├─ injection (sync paste → executor)
                                                      └─ IPC / TUI fan-out
```

**Rule:** If it's in the sounddevice callback, ~10 lines max, never block.

### Practical build order (Phases 4 + 5 coupled)

1. PTT hotkey triggers capture
2. Capture → Groq → terminal text (Phases 1–2)
3. Clipboard paste injection (Phase 5)
4. Minimal cleanup (Phase 5.5)
5. *Then* toggle mode, keystroke injection, daemon IPC split, Deepgram streaming

Phase 6 (daemon IPC) can follow a working **single-process** headless loop.

---

## 3. Gaps the first plan missed (cross-validation catches)

1. No designated **primary platform** — fixed: Windows first.
2. Post-processing was **Phase 9** — fixed: **Phase 5.5** on critical path.
3. State machine only at daemon phase — fixed: sketch Phase 2.
4. Injection strategies listed as equal A/B — fixed: paste primary, keystrokes secondary.

---

## 4. What was built (Phase 0 — same session)

Phase 0 was implemented after planning:

- `navi` CLI: `start`, `tui` (stub), `config`, `doctor`
- Pydantic config + TOML via `ConfigManager`
- Keyring secrets for groq/deepgram/assemblyai/gladia
- Logging: file + console + ring buffer
- 20 pytest tests, ruff, README
- `AGENTS.md` + `ROADMAP.md` Phase 0 items checked off

See `AGENTS.md` §3 and §5 for current tree.

---

## 5. Open questions (carried forward)

- Popup mechanism per platform (Phase 8 spike).
- Default UX: streaming vs batch (interface supports both).
- Wayland injection/hotkey fallbacks (post-Windows).
- How aggressive default post-processing (Phase 5.5 / 9).
- When to invest in native helper for hotkeys and/or injection.
- Local STT (e.g. faster-whisper): out of scope for BYOK v1; leave room in capability flags.

---

## 6. File map (where to read more)

| Topic | File |
|-------|------|
| Mission, decisions, current state | `AGENTS.md` |
| Ordered phases & checkboxes | `docs/ROADMAP.md` |
| Agent must keep docs current | `.cursor/rules/maintain-agents-md.mdc` |
| This recovery doc | `docs/RESEARCH-NOTES.md` |
