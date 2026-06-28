# Navi daemon — background service notes

Navi runs as a **foreground daemon** for now: `navi start` blocks in the terminal,
listens for hotkeys, and serves IPC on localhost.

## IPC

- State file: `daemon.json` under the Navi state directory (ports, PID, auth token)
- Lock file: `daemon.lock` (single-instance guard)
- Command port: request/response NDJSON (`ping`, `get_status`, `patch_config`, …)
- Event port: push stream for logs, state, transcripts, mic level

Clients: `navi tui`, `navi status`, `navi stop`, and `navi config set-key` (when
daemon is running).

## Optional auto-start (not implemented)

### Linux (systemd user unit)

Create `~/.config/systemd/user/navi.service`:

```ini
[Unit]
Description=Navi voice dictation daemon

[Service]
ExecStart=%h/.local/bin/navi start
Restart=on-failure

[Install]
WantedBy=default.target
```

Then: `systemctl --user enable --now navi.service`

### macOS (launchd)

Use a `LaunchAgent` plist pointing at your `navi start` wrapper.

### Windows

Use Task Scheduler to run `navi start` at logon, or a third-party service wrapper.

Background/detached mode may be added in a future release; MVP expects a visible
terminal or service manager.
