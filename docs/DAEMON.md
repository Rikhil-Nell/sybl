# sybl daemon — background service notes

sybl runs as a **foreground daemon** for now: `sybl start` blocks in the terminal,
listens for hotkeys, and serves IPC on localhost.

## IPC

- State file: `daemon.json` under the sybl state directory (ports, PID, auth token)
- Lock file: `daemon.lock` (single-instance guard)
- Command port: request/response NDJSON (`ping`, `get_status`, `patch_config`, …)
- Event port: push stream for logs, state, transcripts, mic level

Clients: `sybl tui`, `sybl status`, `sybl stop`, and `sybl config set-key` (when
daemon is running).

## Optional auto-start (not implemented)

### Linux (systemd user unit)

Create `~/.config/systemd/user/sybl.service`:

```ini
[Unit]
Description=sybl voice dictation daemon

[Service]
ExecStart=%h/.local/bin/sybl start
Restart=on-failure

[Install]
WantedBy=default.target
```

Then: `systemctl --user enable --now sybl.service`

### macOS (launchd)

Use a `LaunchAgent` plist pointing at your `sybl start` wrapper.

### Windows

Use Task Scheduler to run `sybl start` at logon, or a third-party service wrapper.

Background/detached mode may be added in a future release; MVP expects a visible
terminal or service manager.
