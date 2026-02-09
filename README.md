# faaadmv

> Renew your vehicle registration from the terminal.

faaadmv is a REPL-first CLI tool that automates DMV vehicle registration renewal via Playwright. The primary workflow is interactive and designed for manual verification.

## Features

- **REPL-First Workflow** - One command opens an interactive menu
- **Status Check** - View registration status without logging in
- **Renewal with Dry-Run** - Validate eligibility and fees without payment
- **Watch Mode** - Headed browser with slow motion and pause for inspection
- **Local Artifacts** - Screenshots and debug logs saved locally
- **Secure Storage** - Config and payment data stored on your machine

## Installation

```bash
uv pip install faaadmv

# Install browser (first time only)
playwright install chromium
```

## Quick Start (REPL)

```bash
faaadmv
```

In the REPL:
- `a` Add a vehicle
- `s` Check registration status
- `d` Renew (dry-run)
- `r` Renew registration
- `x` Remove a vehicle
- `m` Set default vehicle (when multiple)
- `w` Toggle watch mode
- `q` Quit

## Legacy Commands (still supported)

The REPL is the primary workflow, but these commands remain for scripting:

```bash
faaadmv register
faaadmv status
faaadmv renew
faaadmv vehicles
```

Common options:
- `register --vehicle --payment --verify --reset`
- `status --plate --all --verbose --headed`
- `renew --dry-run --plate --verbose --headed`

## Artifacts and Logs

- Debug log: `~/Library/Application Support/faaadmv/debug.log`
- Screenshots: `~/Library/Application Support/faaadmv/artifacts/`

These may include plate/VIN information. Delete them if you do not want local traces.

## Supported States

| State | Status |
|-------|--------|
| California (CA) | Supported |
| Texas (TX) | Planned |
| New York (NY) | Planned |

## Requirements

- Python 3.11+
- macOS, Linux, or Windows
- Valid smog certification (CA)
- Current insurance on file with DMV

## Development

```bash
# Clone the repo
git clone https://github.com/yourusername/faaadmv
cd faaadmv

# Install in dev mode
uv pip install -e ".[dev]"

# Manual testing
faaadmv
```

Automated tests are currently removed; see `docs/TESTING.md` for manual testing guidance.

## Documentation

- `docs/ARCHITECTURE.md`
- `docs/DATA_MODELS.md`
- `docs/SECURITY.md`
- `docs/PROVIDERS.md`
- `docs/TESTING.md`
- `docs/PROJECT_STRUCTURE.md`

## Disclaimer

This tool automates publicly available DMV web portals. You are responsible for ensuring all information is accurate and for any transactions initiated. The developers are not liable for failed transactions or fees incurred.
