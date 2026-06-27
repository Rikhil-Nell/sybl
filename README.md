# Navi

Open-source, bring-your-own-key (BYOK) voice dictation. Put your cursor anywhere,
hit a global shortcut, speak, and Navi transcribes it and types it in for you.

## Quick start

```powershell
uv sync
uv run navi doctor
uv run navi config init
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
to confirm your voice was captured at 16 kHz mono.

Optional: run the full test suite (excludes mic hardware tests):

```powershell
uv run pytest -m "not integration"
```

To include a real-microphone integration test:

```powershell
uv run pytest -m integration
```

See [AGENTS.md](AGENTS.md) for the project mission and [docs/ROADMAP.md](docs/ROADMAP.md)
for the phased plan.
