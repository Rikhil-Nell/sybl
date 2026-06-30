# CLI reference

The sybl CLI is **scriptable-first**: every operation works with flags, machine-readable
`--json` output is available where it matters, and interactive wizards are opt-in and
TTY-gated. Run `sybl` with no subcommand to see categorized help and the ASCII banner.

## Help layout

Commands are grouped into Rich help panels:

| Panel | Commands |
| --- | --- |
| **Daemon** | `start`, `stop`, `restart`, `status`, `logs` |
| **Dictation** | `audio`, `transcribe`, `hotkey` |
| **Configuration** | `config`, `setup`, `providers` |
| **Diagnostics** | `doctor`, `tui` |

Global options apply to all subcommands:

```powershell
sybl --verbose   # or -v — debug logging where supported
sybl --no-input  # disable interactive prompts and wizards
```

## Banner and first run

- **Bare `sybl`** (no subcommand) prints the ASCII banner and full help.
- **First command** after install also prints the banner once to stderr, then sets
  `ui.first_run_shown = true` in config (via the daemon when it is running).

Banner art lives in `sybl/cli/assets/banner.txt` inside the package.

## Daemon commands

```powershell
sybl start              # background daemon (default)
sybl start --foreground # block in foreground for debugging
sybl stop
sybl restart            # stop (if running) then start detached
sybl status
sybl status --json
sybl logs               # last 50 lines of the daemon log file
sybl logs -n 200        # last 200 lines
sybl logs --follow      # tail -f (requires a TTY)
```

`restart` waits up to 10 seconds for the old daemon to exit before starting a new one.

## Configuration commands

```powershell
sybl config init
sybl config show
sybl config show --json
sybl config get hotkey.mode
sybl config set hotkey.mode both
sybl config set indicator.strategy orb
sybl config edit         # open in $VISUAL / $EDITOR, reload daemon
sybl config set-key groq # interactive when no provider arg + TTY
sybl config keys
sybl config path
sybl config vocab add|list|remove <term>
```

### Dotted paths (`config get` / `config set`)

Paths use dot notation matching the Pydantic config tree, e.g. `provider.preferred`,
`hotkey.binding`, `indicator.orb_accent`.

Values for `config set` are parsed as JSON when possible (`true`, `false`, numbers,
quoted strings, arrays). Examples:

```powershell
sybl config set provider.preferred deepgram
sybl config set indicator.enabled false
sybl config set indicator.orb_fps 45
```

When the daemon is running, `config set` patches the live daemon via IPC (same authority
as the TUI). When it is stopped, changes are written to `config.toml` on disk.

## Setup wizard

```powershell
sybl setup
```

Interactive first-run flow (requires a TTY; blocked by `--no-input`):

1. Pick STT provider (arrow keys)
2. Enter API key (hidden prompt)
3. Pick hotkey mode (`ptt`, `toggle`, or `both`)
4. Optional mic smoke test
5. Sets `provider.preferred`, stores the key, marks `ui.onboarding_complete` and
   `ui.first_run_shown`

For scripts, use `sybl config set-key <provider>` and `sybl config set` instead.

## Providers

```powershell
sybl providers
sybl providers --json
```

Lists registered STT providers with streaming/partial capability flags and whether an
API key is configured in the keyring. Does not expose key material.

Example `--json` shape:

```json
{
  "providers": [
    {
      "name": "groq",
      "streaming": false,
      "partial_results": false,
      "requires_key": true,
      "key_configured": true
    }
  ]
}
```

## Machine-readable output (`--json`)

| Command | `--json` output |
| --- | --- |
| `status` | Daemon state, provider, hotkey, audio device, version, uptime |
| `doctor` | `{ "checks": [...], "ok": true/false }` |
| `config show` | Full effective config object (no secrets) |
| `providers` | Provider list with capabilities and key status |

Use `--json` in scripts and agents; human-readable tables/text are the default.

## Exit codes

Stable exit codes for automation (`sybl/cli/exit_codes.py`):

| Code | Meaning |
| --- | --- |
| `0` | Success |
| `1` | General error (e.g. doctor failure, log file missing) |
| `2` | Usage error (bad args, non-interactive wizard) |
| `3` | Daemon not running (`status`) |
| `4` | Config error (invalid path/value, init conflict) |
| `5` | IPC error (daemon unreachable) |
| `6` | Secrets/keyring error |

## `--no-input` and interactivity

Pass `--no-input` (anywhere before the subcommand) to:

- Skip `sybl setup`
- Require an explicit provider argument for `config set-key`
- Refuse hidden API-key prompts

Wizards and prompts also require stdin and stdout to be TTYs. Piping or CI runs stay
non-interactive by default.

## Related docs

- [Configuration](configuration.md) — `config.toml` keys
- [Getting started](getting-started.md) — install and first dictation
- [Overlay indicator](OVERLAY.md) — glass orb (`indicator.strategy = orb`)
