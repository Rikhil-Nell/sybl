# sybl v0.1.2 — TUI design spec

> Approved direction from Lavish review (2026-06-28). Interactive mocks live in
> `.lavish/`. This doc is the Textual implementation reference.

## Design system: Sibyl Royal

Flat palette — no gradients, no glow. Ancient/regal blue + gold.

| Token | Value | Use |
| --- | --- | --- |
| `--bg-base` | `#080e1a` | Terminal background |
| `--bg-panel` | `#0c1633` | Chrome, modals, selected rows |
| `--bg-panel-2` | `#102040` | Context strip, footer |
| `--border` | `#1e3a6e` | Primary borders |
| `--border-dim` | `#152a52` | Inner dividers |
| `--text` | `#e8e4d9` | Body |
| `--text-muted` | `#7a8aa8` | Labels, timestamps |
| `--gold` | `#b8860b` | Accents, keys, zone headers |
| `--gold-bright` | `#c9a227` | Brand, active nav, listening |
| `--live` | `#5a8fc4` | Daemon live, processing, INFO logs |

**Fonts:** IBM Plex Mono (data, labels, logs) + Instrument Sans (brand only).

## Main dashboard (`sybl tui`)

Lavish mock: `.lavish/sybl-v012-tui-mock.html`

### Layout zones (separation of concerns)

Final mission-control layout (Lavish mock `.lavish/sybl-mission-control.html`,
ported faithfully to Textual):

```
┌─ CHROME ─────────────────────────────┐  ✦ sybl · ● live · state … v0.1.x · up · N today
├─ CONTEXT ────────────────────────────┤  mic · provider · hotkey · ipc
├─ HERO ───────────────────────────────┤  ◌ STATE   ▰▰▱▱ meter + label   hint
├─ SESSION ────────┬─ TRANSCRIPTS ──────┤  left: detail · right(top): history
│  PIPELINE        ├─ LOGS ─────────────┤  right(bottom): log tail
│  PROVIDER        │                    │
│  HOTKEY          │                    │
│  TODAY           │                    │
├─ LIVE ───────────────────────────────┤  streaming partial / last-injected ticker
└─ FOOTER ─────────────────────────────┘  keyboard hints
```

| Zone | Contents | Not here |
| --- | --- | --- |
| **Chrome** | `✦ sybl`, daemon chip, state chip, version · uptime · today count | Device details |
| **Context** | Mic, provider, hotkey binding, IPC | Session state |
| **Hero** | State dot+name, block-glyph RMS meter (IPC `level`), label, hint | Device details |
| **Session** | PIPELINE (capture→transcribe→cleanup→inject) · PROVIDER · HOTKEY · TODAY | Transcripts |
| **Transcripts** | Filter, count header, selectable history (`Nw · Ds · provider`) | Logs |
| **Logs** | Timestamped ring buffer tail | Settings |
| **Live** | Streaming partial while active; last injected text + `“…”` when idle | History |
| **Footer** | `s` settings · `?` help · `/` filter · `y` copy · `↑↓` select · `q` quit | — |

### States (hero band + pipeline)

| State | Dot | Meter | Active stage | Hint example |
| --- | --- | --- | --- | --- |
| IDLE | `◌` gray | empty | none | hold hotkey · double-press to toggle |
| LISTENING | `●` gold | gold fill | capture | Esc cancels · release to send |
| PROCESSING | `●` blue | blue fill | transcribe | {provider} · streaming |
| INJECTING | `●` blue | empty | inject (capture/transcribe ✓) | pasting into focused app |

Box-model note: any single-row bar or `padding-top` label must use a `height`
that clears its padding/border, or the only content row collapses and the text
renders invisible (bit us on the chrome bars and the section titles).

## Settings modal (`s`)

Lavish mock: `.lavish/sybl-v012-settings-mock.html`

Modal overlay on dimmed dashboard — not a full-screen screen swap.

### Navigation (sidebar)

| Section | Settings exposed |
| --- | --- |
| **Provider** | Preferred provider, fallback order, API keys (groq / deepgram) |
| **Hotkey** | Mode (`both` / `ptt` / `toggle`), binding, cancel, `ptt_hold_ms`, `toggle_double_press_ms`, streaming, `min_duration_ms` |
| **Audio** | Input device, sample rate, save last recording |
| **Indicator** | Overlay on/off, size, offset, sound cues (enable, volume, start/stop file, max seconds) |
| **Injection** | Enabled, restore clipboard |
| **Text** | Post-process master + toggles, voice commands, vocabulary enabled |
| **Advanced** | Log level, history size (IPC/logging — power users) |

Vocabulary term list stays CLI (`sybl config vocab`) for v0.1.2; TUI shows enabled toggle + hint.

### Modal chrome

- Title: **Settings** · subtitle: changes apply via daemon immediately
- Left: a **fixed-width section rail** (22 cols) under a `SECTIONS` label with a
  gold active indicator — not half the modal. (The earlier bug: the CSS styled
  `#settings-nav`, but compose yielded the bare `ListView#settings-nav-list`, so
  the width never applied and the list grabbed ~half the width.)
- Right: form for the active section only, each with a **gold heading + one-line
  description + underline**, then labeled fields. Sound-cue rows are a single
  line: wide select + compact `Browse…` / `Built-in` buttons.
- Footer: `Esc` back · `↑↓` switch section · edit raw file with `e` on the
  dashboard

### Raw config editing

- Dashboard `e` (and `sybl config edit`) open `config.toml` in `$VISUAL`/`$EDITOR`
  (`sybl/config/edit.py`, per-OS fallback). On return the reloaded file is pushed
  to the daemon via `PATCH_CONFIG` (full dump → deep-merge), so the daemon stays
  the source of truth and there is no TUI/daemon drift.

## Out of scope for v0.1.2 TUI mocks

- Overlay pill visual (separate Windows tkinter component)
- CLI `sybl start` banner
- Marketing / pitch-deck framing inside the TUI

## Textual implementation notes

Implemented in v0.1.2:

| Widget / asset | Path |
| --- | --- |
| Sibyl Royal theme | `sybl/tui/theme/sibyl_royal.tcss` |
| Chrome bar (version/uptime/today) | `sybl/tui/widgets/chrome_bar.py` |
| Context strip | `sybl/tui/widgets/context_strip.py` |
| Hero band (state + glyph meter) | `sybl/tui/widgets/hero_band.py` |
| Session pane (pipeline/provider/hotkey/today) | `sybl/tui/widgets/session_pane.py` |
| Transcript list (filter + count + meta) | `sybl/tui/widgets/transcript_list.py` |
| Log band | `sybl/tui/widgets/log_band.py` |
| Live band (streaming / last-injected) | `sybl/tui/widgets/live_band.py` |
| Key footer | `sybl/tui/widgets/key_footer.py` |
| Dashboard screen | `sybl/tui/screens/dashboard.py` |
| Settings modal (sidebar) | `sybl/tui/screens/settings.py` |
| Help overlay | `sybl/tui/screens/help.py` |

- Theme loaded via `SyblTuiApp.CSS_PATH`; IPC `level` events drive the session meter.
- Settings stays a `ModalScreen` overlay; all writes use existing `TuiIpcClient` methods.
- Tests: `tests/test_tui_dashboard.py`, extended `tests/test_tui_settings.py`.
