# sybl daemon — background service notes

sybl runs as a **background process** by default: `sybl start` spawns a detached
daemon, writes logs to the log file, and returns your terminal immediately.

Use **`sybl tui`** for live logs, history, and settings. Use **`sybl stop`** to shut
down. Use **`sybl start --foreground`** when debugging (blocks the terminal, prints
logs to stderr).

## IPC

- State file: `daemon.json` under the sybl state directory (ports, PID, auth token)
- Lock file: `daemon.lock` (single-instance guard)
- Command port: request/response NDJSON (`ping`, `get_status`, `patch_config`, …)
- Event port: push stream for logs, state, transcripts, mic level

Clients: `sybl tui`, `sybl status`, `sybl stop`, and `sybl config set-key` (when
daemon is running).

## Optional auto-start (system service)

`sybl start` already detaches on all platforms (Windows, Linux, macOS). For login
auto-start, point your service manager at the same command.

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

Use `sybl stop` / `sybl start` for manual control; the unit wraps the same background
spawn.

### macOS (launchd)

Use a `LaunchAgent` plist with `ProgramArguments` set to your `sybl` binary and
`start` (no `--foreground`).

### Windows

`sybl start` already uses a detached process (no console window). For logon
auto-start, use Task Scheduler with action `sybl start`.
