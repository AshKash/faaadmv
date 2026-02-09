# AGENTS.md — Agent Entry Point

> This file is read automatically by Codex at session start.
> It tells any agent how to navigate, build, test, and contribute to this project.

## Project Overview

**faaadmv** is a Python REPL-first CLI tool that automates California DMV vehicle registration renewal via browser automation (Playwright). Users register their vehicle/payment info once, then check status and renew from the terminal.

**Stage:** MVP (v0.1.0) — single state (CA), core flows working.

## Quick Setup

```bash
# Create venv and install (editable + dev deps)
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"

# Install browser for Playwright
playwright install chromium

# Verify install
faaadmv --version
```

## Manual Testing

```bash
# Start REPL
faaadmv

# In REPL:
# a = add vehicle
# s = status check
# d = renew dry-run
# r = renew
# w = toggle watch mode
```

See `docs/TESTING.md` for the full manual checklist.

## Project Structure

```
src/faaadmv/
  cli/
    app.py              # Typer app — commands: register, status, renew
    repl.py             # REPL (primary UX)
    commands/
      register.py       # Interactive setup (vehicle + owner + payment)
      status.py         # Check registration via DMV portal
      renew.py          # Full renewal flow with payment
    ui.py               # Rich panels, tables, formatting helpers
  core/
    config.py           # ConfigManager — encrypted config load/save
    crypto.py           # Fernet + scrypt key derivation
    keychain.py         # OS keychain wrapper (payment storage)
    browser.py          # Playwright browser lifecycle
    captcha.py          # CAPTCHA detection + solving
  models/
    vehicle.py          # VehicleInfo (plate + VIN validation)
    owner.py            # OwnerInfo + Address
    payment.py          # PaymentInfo (Luhn, SecretStr, masking)
    config.py           # UserConfig (serialization envelope)
    results.py          # RegistrationStatus, FeeBreakdown, RenewalResult
  providers/
    base.py             # BaseProvider ABC — abstract DMV interface
    ca_dmv.py           # California DMV implementation
    registry.py         # Provider discovery (get_provider("CA"))
  exceptions.py         # Full exception hierarchy

docs/                   # Design documentation
  ARCHITECTURE.md       # System layers and data flow
  DATA_MODELS.md        # Pydantic model reference
  PROVIDERS.md          # Provider interface + CA DMV details
  SECURITY.md           # Encryption, keychain, threat model
  TESTING.md            # Manual testing guide
  PROJECT_STRUCTURE.md  # Directory layout

AGENTS.md               # This file
STATUS.md               # Feature implementation status
PRD.md                  # Product requirements document
```

## Key Conventions

- **Python 3.11+**, Pydantic v2, async/await throughout
- **Typer** for CLI, **Rich** for terminal UI
- **Absolute imports** only: `from faaadmv.models import VehicleInfo`
- **SecretStr** for all sensitive fields (card number, CVV)
- Payment data stored in **OS keychain** (via `keyring`), never in config file
- Config file is **Fernet-encrypted** with user passphrase (scrypt KDF)
- Line length 88, formatter/linter is `ruff`
- Type checking with `mypy --strict`

## REPL Actions

- `a` Add a vehicle
- `s` Status check
- `d` Renew (dry-run)
- `r` Renew
- `x` Remove a vehicle
- `m` Set default vehicle (when multiple)
- `w` Toggle watch mode
- `q` Quit

## Architecture Overview

```
CLI Layer (Typer + Rich)
  REPL (primary) | register | status | renew
            ↓
Core Services Layer
  ConfigManager │ BrowserManager │ CaptchaSolver │ PaymentKeychain
            ↓
Provider Layer
  BaseProvider (ABC) → CADMVProvider (California)
            ↓
External Services
  DMV Web Portal (Playwright) │ OS Keychain (keyring)
```

## Exception Hierarchy

```
FaaadmvError
├── ConfigError
│   ├── ConfigNotFoundError
│   ├── ConfigDecryptionError
│   └── ConfigValidationError
├── BrowserError
│   ├── NavigationError
│   ├── TimeoutError
│   └── SelectorNotFoundError
├── DMVError
│   ├── VehicleNotFoundError
│   ├── EligibilityError
│   ├── SmogCheckError
│   ├── InsuranceError
│   ├── PaymentError
│   │   └── PaymentDeclinedError
│   └── (base DMVError for unknown portal errors)
└── CaptchaError
    ├── CaptchaDetectedError
    └── CaptchaSolveFailedError
```

## CA DMV Provider Notes

The status check is a **multi-step form** (verified against real CA DMV 2026-02-07):

1. Navigate to `https://www.dmv.ca.gov/wasapp/rsrc/vrapplication.do`
2. Enter license plate in `#licensePlateNumber` → Submit
3. Enter VIN (last 5) in `#individualVinHin` → Submit
4. Parse results from `<fieldset>` containing prose paragraphs

The results page returns **prose text** (not structured data). The provider maps prose to `StatusType` via `_determine_status_from_text()`:
- "has been mailed" / "was mailed" → `CURRENT`
- "in progress" / "not yet been mailed" / "not yet received" → `PENDING`
- "items due" / "action is required" → `HOLD`
- "expired" → `EXPIRED`

## Test Data (Safe for Commits)

All test data uses well-known test values:
- Cards: `4242424242424242` (Visa), `5555555555554444` (MC), `378282246310005` (Amex)
- Names/addresses: `Jane Doe`, `123 Main St`, `Los Angeles, CA 90001`
- Vehicles: plate `8ABC123`, VIN `12345`

No real PII or payment data exists in this repository.
