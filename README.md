# Navi



Open-source, bring-your-own-key (BYOK) voice dictation. Put your cursor anywhere,

hit a global shortcut, speak, and Navi transcribes it and types it in for you.



## Quick start



```powershell

uv sync

uv run navi doctor

uv run navi config init

uv run navi config set-key groq

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



## Transcribe speech (Phase 2)



Store your Groq API key in the OS keyring, then record and transcribe:



```powershell

uv run navi config set-key groq

uv run navi transcribe --seconds 5

```



Speak during the recording window — Navi sends 16 kHz mono audio to Groq and

prints the transcript with provider and latency metadata.



Configure the Groq model in `config.toml` under `[provider.groq]` (default:

`whisper-large-v3-turbo` for speed; use `whisper-large-v3` for higher accuracy).



Optional: run the full test suite (excludes mic hardware and live API tests):



```powershell

uv run pytest -m "not integration"

```



To include real-hardware or live-provider integration tests:



```powershell

uv run pytest -m integration

```



See [AGENTS.md](AGENTS.md) for the project mission and [docs/ROADMAP.md](docs/ROADMAP.md)

for the phased plan.

