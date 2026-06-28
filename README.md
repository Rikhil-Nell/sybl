# sybl

**Open-source, bring-your-own-key voice dictation.** Put your cursor anywhere, hold a
global shortcut, speak, and sybl transcribes it fast — then types it in for you.

The open-source alternative to closed dictation tools like Wispr Flow. No subscription,
no sybl-hosted backend: your audio goes straight to the STT provider you choose.

[![CI](https://github.com/Rikhil-Nell/sybl/actions/workflows/ci.yml/badge.svg)](https://github.com/Rikhil-Nell/sybl/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/sybl.svg)](https://pypi.org/project/sybl/)

## Features

- **Global push-to-talk** — hold a system-wide hotkey, speak, release to finish
- **BYOK STT** — Groq Whisper (batch) and Deepgram (streaming) today; pluggable providers
- **Types where you were focused** — clipboard-paste injection on Windows
- **Daemon + TUI** — background service with a Textual dashboard for logs, history, and settings
- **Listening pill** — small overlay near your cursor while dictating (Windows)
- **Custom vocabulary** — STT hints for names and jargon via `sybl config vocab`
- **Voice commands** — `new line`, `period`, `comma` in final transcripts
- **Local-first** — no telemetry; API keys in the OS keyring

## Install

```powershell
pipx install sybl
```

Or with [uv](https://docs.astral.sh/uv/):

```powershell
uv tool install sybl
```

Requires **Python 3.12+**. Windows is the primary supported platform for the full
core loop (hotkeys, injection, indicator).

## Quick start

```powershell
sybl doctor
sybl config init
sybl config set-key groq
sybl start
```

In another terminal:

```powershell
sybl tui
```

Hold **Ctrl+Alt+Space** (default), speak, release — the transcript is pasted into
whatever app had focus. Press **Esc** while holding to cancel.

See [Getting started](docs/getting-started.md) for the full walkthrough.

## Documentation

| Doc | Description |
| --- | --- |
| [Getting started](docs/getting-started.md) | Install, first run, daemon + TUI |
| [Providers](docs/providers.md) | Groq & Deepgram BYOK setup |
| [Configuration](docs/configuration.md) | `config.toml` reference |
| [Permissions](docs/permissions.md) | Microphone and injection notes |
| [Development](docs/DEVELOPMENT.md) | Local dev, phases, integration tests |
| [Roadmap](docs/ROADMAP.md) | What's built and what's next |
| [Daemon architecture](docs/DAEMON.md) | IPC and process model |

## Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md)
for architecture and conventions.

## License

[MIT](LICENSE) © Rikhil Nellimarla
