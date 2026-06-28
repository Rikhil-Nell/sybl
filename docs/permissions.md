# Permissions

Navi needs microphone access for dictation and (on Windows) the ability to paste
text into other applications.

## Windows (supported)

### Microphone

- Grant microphone access in **Settings → Privacy & security → Microphone**.
- Ensure your terminal / Python is allowed if prompted.
- Run `navi doctor` and `navi audio record --seconds 3` to verify capture.

Bluetooth headsets can disconnect mid-session; Navi handles stream errors gracefully
but you may need to restart the daemon after reconnecting.

### Text injection

Navi's primary injection strategy is **clipboard set + simulated Ctrl+V** (`SendInput`).
This works in most standard text fields without elevated privileges.

Known limitations:

- Some apps block synthetic input or clipboard paste (certain secure fields, some games).
- UAC-elevated windows may not receive paste from a non-elevated daemon.
- Remote desktop and some VM setups can behave differently.

If paste fails, set `inject.enabled = false` to debug STT only, or copy from TUI history.

### Global hotkeys

`pynput` listens for system-wide key events. Admin-only apps or aggressive security
software may interfere. Test with `navi hotkey test`.

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

- API keys: OS keyring only
- Audio: sent to your configured STT provider during active sessions only
- Transcripts: kept in local daemon history (configurable size); not sent to Navi servers
- Debug WAV: optional last recording saved locally when `save_last_recording = true`

See [SECURITY.md](../SECURITY.md) for vulnerability reporting.
