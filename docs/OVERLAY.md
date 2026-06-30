# Capture overlay (listening pill)

sybl shows a **Qt dock pill** at the top center of the screen while you dictate.
It slides down on listen, shows voice-reactive wave bars, an elapsed timer, and
switches to a spinner during transcribing.

PySide6 ships as a **core dependency** — a normal `uv tool install sybl` or
`pipx install sybl` install includes everything. No extras required.

## Config

Default (no changes needed):

```toml
[indicator]
enabled = true
strategy = "pill"
anchor = "top_center"
margin_px = 0
```

Legacy `strategy = "overlay"` or `"orb"` in older configs is normalized to `"pill"`.
Set `strategy = "none"` to disable the on-screen cue.

## How it works

The pill runs in a **separate overlay process** (`python -m sybl.indicator.pill_qt`)
controlled by the daemon over stdin NDJSON:

| Command | Effect |
|---------|--------|
| `show` | Slide pill down, reset to listening phase |
| `hide` | Slide pill up |
| `level` | RMS mic level (0–1) for wave bars |
| `phase` | `"listening"` or `"processing"` |
| `config` | Accent colors, margin, etc. |

Implementation: `sybl/indicator/pill_qt/` (QML + host), wrapper in
`sybl/indicator/pill_qt_win.py`.

## Keys

| Key | Default | Notes |
|-----|---------|-------|
| `anchor` | `"top_center"` | Dock placement |
| `margin_px` | `0` | Inset below top work-area edge |
| `orb_accent` / `orb_accent_secondary` | purple / orange | Wave bar colors |

## Preview without the daemon

```powershell
sybl indicator demo
# or
uv run python scripts/show_pill.py
```

## Platform support

- **Windows** — primary target
- **macOS / Linux** — pill not implemented yet; degrades to no-op (dictation unaffected)

## See also

- [Configuration](configuration.md) — full `[indicator]` reference
- [Popup spike](POPUP-SPIKE.md) — early indicator research
