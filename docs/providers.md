# STT providers (BYOK)

sybl does not host transcription. You bring your own API key; audio is sent directly
from your machine to the provider you configure.

## Supported providers

| Provider | Mode | Best for |
| --- | --- | --- |
| **Groq** | Batch (record → upload) | Fastest setup; good default for PTT |
| **Deepgram** | Streaming WebSocket + batch | Live partials; lower perceived latency |

More providers (AssemblyAI, Gladia, etc.) are planned — see [ROADMAP.md](ROADMAP.md).

## Store API keys

Keys are stored in the OS keyring via the CLI:

```powershell
sybl config set-key groq
sybl config set-key deepgram
```

Never put API keys in `config.toml` or commit them to git.

## Choose a provider

In `config.toml`:

```toml
[provider]
preferred = "groq"
fallback_order = ["deepgram", "groq"]
```

Fallback runs at **session start** only (when the daemon resolves a provider), not
mid-stream.

## Groq (Whisper)

Batch transcription through Groq's Whisper API. Default model:

```toml
[provider.groq]
model = "whisper-large-v3-turbo"   # speed (default)
# model = "whisper-large-v3"       # accuracy
language = null                     # auto-detect
temperature = 0.0
```

One-shot test without the daemon:

```powershell
sybl config set-key groq
sybl transcribe --seconds 5
```

### Vocabulary hints

User terms from `vocabulary.toml` are appended to Groq's Whisper `prompt` at session
start (helps with names and jargon).

## Deepgram

Streaming via WebSocket; also supports batch REST.

```toml
[provider.deepgram]
model = "nova-3"
punctuate = true
smart_format = true
interim_results = true
language = null
```

Streaming test:

```powershell
sybl config set-key deepgram
sybl transcribe --seconds 5 --stream
```

### Vocabulary hints

User terms are sent as Deepgram **keyterms** at session start.

## Streaming vs batch in the daemon

Under `[hotkey]`:

```toml
streaming = "auto"   # stream when the resolved provider supports it
# streaming = "on"   # force streaming
# streaming = "off"  # force batch
```

With `auto` and Groq as preferred, dictation uses batch. With Deepgram preferred,
dictation streams audio and assembles the final transcript from final + trailing
interim segments.

## Costs and privacy

- You pay your provider directly per their pricing.
- sybl sends audio only during active transcription sessions.
- No sybl telemetry or cloud storage of transcripts (history is local in the daemon).

## Adding a provider (contributors)

See [AGENTS.md](../AGENTS.md) for the streaming-first `Provider` interface and
`ProviderManager` selection logic.
