# Permissions

sybl needs microphone access for dictation and (on Windows) the ability to paste
text into other applications.

## Windows (supported)

### Microphone

- Grant microphone access in **Settings → Privacy & security → Microphone**.
- Ensure your terminal / Python is allowed if prompted.
- Run `sybl doctor` and `sybl audio record --seconds 3` to verify capture.

Bluetooth headsets can disconnect mid-session; sybl handles stream errors gracefully
but you may need to restart the daemon after reconnecting.

### Text injection

sybl's primary injection strategy is **clipboard set + simulated Ctrl+V** (`SendInput`).
This works in most standard text fields without elevated privileges.

Known limitations:

- Some apps block synthetic input or clipboard paste (certain secure fields, some games).
- UAC-elevated windows may not receive paste from a non-elevated daemon.
- Remote desktop and some VM setups can behave differently.

If paste fails, set `inject.enabled = false` to debug STT only, or copy from TUI history.

### Global hotkeys

`pynput` listens for system-wide key events. Admin-only apps or aggressive security
software may interfere. Test with `sybl hotkey test`.

## macOS

**Not yet supported** for the full core loop (hotkeys, injection, indicator are stubs).
Doctor may report missing platform backends.

Expected future requirements:

- Microphone permission (TCC)
- Accessibility permission for synthetic input / paste

## Linux

**Not yet supported** for the full core loop.

Expected future considerations:

- PulseAudio/PipeWire device selection
- Wayland text injection is significantly harder than X11 — likely needs a native helper

## Privacy

- API keys: OS keyring only (see below)
- Audio: sent to your configured STT provider during active sessions only
- Transcripts: kept in local daemon history (configurable size); not sent to sybl servers
- Debug WAV: optional last recording saved locally when `save_last_recording = true`

## Secrets and the OS keyring

sybl stores provider API keys in the **OS keyring**, not in `config.toml`. You set
them with `sybl config set-key <provider>`.

| Stored in | Examples |
| --- | --- |
| `config.toml` | Hotkey, provider name, post-process flags — safe to back up |
| OS keyring | Groq, Deepgram, etc. API keys |

**Threat model:** the keyring is **per user account**, not per application. Any
program running as you could read entries if it knows the service name (`sybl`).
This is standard for desktop CLI tools — much safer than plaintext config files,
but not malware-proof. See `sybl doctor` for keyring backend status.

For deeper live checks (network, mic, clipboard), run `sybl doctor --live`.

See [SECURITY.md](../SECURITY.md) for vulnerability reporting.
