# Capture overlay (listening indicator)

While dictating, sybl can show a small on-screen indicator so you know the mic is live.
The default on Windows is a **tkinter pill** near the cursor (`indicator.strategy =
"overlay"`). For a dock-style Qt pill at the top of the screen, use the optional
**pill** strategy.

## Strategies

| `indicator.strategy` | Behavior |
| --- | --- |
| `"overlay"` | Windows tkinter pill near cursor (default) |
| `"pill"` | Qt dock pill — slides from top, voice-reactive waves, transcribing spinner (requires `sybl[pill]`, Windows) |
| `"none"` | No on-screen indicator |

`strategy = "orb"` in older configs is accepted and normalized to `"pill"`.

Sound cues (`indicator.sound_*`) work with any strategy.

## Install the pill extra

`PySide6` is a small pip extra for the Qt pill overlay.

```powershell
uv tool install "sybl[pill]"
```

Or with pip/pipx:

```powershell
pipx install "sybl[pill]"
pip install "sybl[pill]"
```

Enable in config:

```powershell
sybl config set indicator.strategy pill
sybl config set indicator.anchor top_center
sybl restart
```

Or edit `config.toml`:

```toml
[indicator]
strategy = "pill"
anchor = "top_center"
```

## Pill behavior

The pill runs in a **separate overlay process** (`python -m sybl.indicator.pill_qt`)
spawned by the daemon. That keeps the Qt UI off the asyncio event loop.

- Top-center dock placement on the active monitor
- Slides down from the top edge when you start dictating
- **Listening:** voice-reactive wave bars (sybl purple/orange accents)
- **Transcribing:** arc spinner + label; stays visible through STT and inject
- Slides back up when the session returns to idle
- Frameless, transparent, always-on-top, click-through
- Commands over stdin as **NDJSON** lines: `show`, `hide`, `level`, `phase`, `config`, `quit`

Implementation: `sybl/indicator/pill_qt/` (QML + host), wrapper in
`sybl/indicator/pill_qt_win.py`.

## Configuration

| Key | Default | Description |
| --- | --- | --- |
| `anchor` | `"top_center"` | Dock pill placement (`top_center` recommended) |
| `margin_px` | `0` | Distance below the top work-area edge when visible |
| `orb_accent` | `"#7b2ff7"` | Primary wave color (purple) |
| `orb_accent_secondary` | `"#f97316"` | Secondary wave color (orange) |

See [configuration.md](configuration.md#indicator) for the full table.

## Fallback chain

When `strategy = "pill"`, `create_indicator()` tries:

1. **Qt pill** — if `PySide6` is installed (Windows)
2. **tk overlay** — Windows pill near cursor
3. **No-op**

## Platform notes

- **Windows** — primary target for the Qt dock pill
- **macOS / Linux** — Qt pill not implemented in this release

## See also

- [Configuration](configuration.md) — full `[indicator]` table
- [Popup spike](POPUP-SPIKE.md) — original tk overlay research
