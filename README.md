# faaadmv

> Renew your vehicle registration from the command line.

faaadmv is an interactive CLI tool that automates DMV vehicle registration renewal. No more fighting with government websites.

## Features

- **Interactive Setup** - Guided wizard to save your vehicle and payment info
- **Status Check** - See your registration status without logging in
- **One-Command Renewal** - Complete renewal with a single command
- **Secure Storage** - Credentials encrypted locally, payment in OS keychain
- **Dry Run Mode** - Test the full flow without making a payment

## Installation

```bash
uv pip install faaadmv

# Install browser (first time only)
playwright install chromium
```

## Quick Start

```bash
# Set up your vehicle info (interactive)
faaadmv register

# Check your registration status
faaadmv status

# Renew your registration
faaadmv renew
```

## Commands

### `faaadmv register`

Interactive setup wizard to save your vehicle, owner, and payment information.

```bash
$ faaadmv register

  Welcome to faaadmv! Let's set up your vehicle.

  ─── Vehicle Information ───
  ? License plate number: 8ABC123
  ? Last 5 digits of VIN: 12345
  ...

  ✓ Configuration saved securely.
```

Options:
- `--vehicle` - Update vehicle info only
- `--payment` - Update payment info only
- `--verify` - Show saved config (masked)
- `--reset` - Delete all saved data

### `faaadmv status`

Check your current registration status.

```bash
$ faaadmv status

  ┌─────────────────────────────────┐
  │ 2019 Honda Accord               │
  │ Plate: 8ABC123                  │
  ├─────────────────────────────────┤
  │ Status:     ✓ Current           │
  │ Expires:    June 20, 2026       │
  │ Days left:  133                 │
  └─────────────────────────────────┘
```

### `faaadmv renew`

Complete your registration renewal with payment.

```bash
$ faaadmv renew

  ✓ Smog Check: Passed
  ✓ Insurance: Verified

  ┌─────────────────────────────────┐
  │ Registration Fees               │
  ├─────────────────────────────────┤
  │ Registration Fee      $168.00   │
  │ CHP Fee                $32.00   │
  │ County Fee             $48.00   │
  ├─────────────────────────────────┤
  │ Total                 $248.00   │
  └─────────────────────────────────┘

  ⚠️  Pay $248.00 now? [y/N]: y

  ✓ Payment successful!
  ✓ Receipt saved to ./dmv_receipt_2026-02-07.pdf
```

Options:
- `--dry-run` - Run without making payment
- `--headed` - Show browser (for CAPTCHA)
- `--verbose` - Show detailed output

## Supported States

| State | Status |
|-------|--------|
| California (CA) | ✓ Supported |
| Texas (TX) | Planned |
| New York (NY) | Planned |

## Security

- **Local Storage Only** - No cloud, no telemetry
- **Encrypted Config** - AES-256 encryption with your passphrase
- **OS Keychain** - Payment data stored in macOS Keychain / Windows Credential Manager
- **Masked Output** - Sensitive data never shown in terminal

See [SECURITY.md](docs/SECURITY.md) for details.

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

# Run tests
pytest

# Run linting
ruff check src tests
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Data Models](docs/DATA_MODELS.md)
- [Security](docs/SECURITY.md)
- [Providers](docs/PROVIDERS.md)
- [Testing](docs/TESTING.md)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Disclaimer

This tool automates publicly available DMV web portals. You are responsible for ensuring all information is accurate and for any transactions initiated. The developers are not liable for failed transactions or fees incurred.
