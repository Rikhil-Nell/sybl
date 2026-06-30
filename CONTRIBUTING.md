# Contributing to sybl

Thanks for helping make sybl better. This project is early but contributor-ready —
issues, docs fixes, and PRs are welcome.

## Before you start

- Read [AGENTS.md](AGENTS.md) for mission, architecture, and conventions.
- Open a GitHub issue before large changes; check open issues for overlap.
- Windows is the primary platform for the core loop; keep platform-specific code
  behind interfaces.

## Development setup

Requirements: **Python 3.12+**, [uv](https://docs.astral.sh/uv/).

```powershell
git clone https://github.com/Rikhil-Nell/sybl.git
cd sybl
uv sync
uv run sybl doctor
```

## Running tests

Prefer the hermetic runner (CI parity — isolated config/state, fixed TZ/LANG):

```powershell
python scripts/run_tests.py
```

On Linux/macOS with bash:

```bash
./scripts/run_tests.sh
```

Or manually:

```powershell
uv run ruff check sybl tests
uv run pytest -m "not integration" -q
```

Integration tests (real hardware / live STT — manual only):

```powershell
uv run pytest -m integration
```

## Dependency policy

All PyPI dependencies use `>=floor,<next_major` upper bounds in `pyproject.toml`.
Post-1.0 packages cap at the next major (e.g. `numpy>=2.0.0,<3`). Reject unbounded
`>=` specs in PRs.

## Pull requests

1. Open an issue first for large features so we can align on approach.
2. Keep PRs focused; match existing style (`ruff`, type hints, async patterns).
3. Update [AGENTS.md](AGENTS.md) if you change behavior, architecture, or project structure.
4. Never commit API keys or secrets.
5. If you touch hotkeys, injection, or the listening indicator, note manual Windows
   testing in the PR description.

Use the PR template checklist when opening a pull request.

## Commit messages

Write clear, concise messages focused on *why*. Do **not** add `Co-authored-by`
trailers for AI tools.

Optional local hook (rejects Cursor co-author trailers):

```powershell
git config core.hooksPath .githooks
```

## Releasing (maintainers)

Releases are tagged `v*` on GitHub; publishing a GitHub Release triggers the PyPI
workflow (`.github/workflows/release.yml`).

**One-time PyPI trusted publishing setup:**

1. Create the `sybl` project on [PyPI](https://pypi.org/) (or claim the name).
2. On PyPI → Your project → Publishing → Add a new pending publisher:
   - Owner: `Rikhil-Nell`
   - Repository: `sybl`
   - Workflow name: `release.yml`
   - Environment name: *(leave blank)*
3. Push a tag and publish a GitHub Release — the workflow builds with `uv build`
   and uploads via OIDC (no long-lived API token required).

**Release checklist (semver patch):**

- [ ] `python scripts/run_tests.py` green locally
- [ ] `CHANGELOG.md` section for the release version complete
- [ ] Bump `version` in `pyproject.toml` and `sybl/__init__.py`
- [ ] `git tag vX.Y.Z` + GitHub Release → PyPI workflow (`release.yml`)
- [ ] README / docs figures still match the UI (regenerate with `scripts/generate_brand_assets.py` if needed)

For local packaging smoke tests:

```powershell
uv build
uv tool install dist/sybl-*.whl --force
sybl doctor
```

## Code of conduct

This project follows the [Contributor Covenant](CODE_OF_CONDUCT.md). Be respectful
and constructive.

## Security

See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.
