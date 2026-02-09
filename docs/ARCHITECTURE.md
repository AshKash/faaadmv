# faaadmv System Architecture

## Overview

faaadmv is a layered CLI application that automates DMV vehicle registration renewal through browser automation. The primary UX is a REPL with a watch mode for manual verification.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      CLI Layer (Typer + Rich)                           │
│  ┌──────────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ REPL (main)  │  │ register │  │  status  │  │  renew   │             │
│  └──────────────┘  └──────────┘  └──────────┘  └──────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Core Services Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │ ConfigManager   │  │ BrowserManager  │  │ CaptchaSolver           │ │
│  │ - load/save     │  │ - launch        │  │ - detect                │ │
│  │ - validate      │  │ - navigate      │  │ - solve (API/manual)    │ │
│  │ - encrypt       │  │ - screenshot    │  │                         │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Provider Layer                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      BaseProvider (ABC)                          │   │
│  │  - get_registration_status()                                     │   │
│  │  - validate_eligibility()                                        │   │
│  │  - submit_renewal()                                              │   │
│  │  - get_selectors()                                               │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                    △                                    │
│                    ┌───────────────┼───────────────┐                   │
│              ┌─────┴─────┐   ┌─────┴─────┐   ┌─────┴─────┐             │
│              │ CADMVProv │   │ TXDMVProv │   │ NYDMVProv │             │
│              │ (CA impl) │   │ (future)  │   │ (future)  │             │
│              └───────────┘   └───────────┘   └───────────┘             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           External Services                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │ DMV Web Portal  │  │ 2Captcha API    │  │ OS Keychain             │ │
│  │ (via Playwright)│  │ (optional)      │  │ (via keyring)           │ │
│  └─────────────────┘  └─────────────────┘  └─────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Responsibilities

### CLI Layer (`faaadmv/cli/`)

| Component | Responsibility |
|-----------|----------------|
| `app.py` | Typer application, command definitions, argument parsing |
| `repl.py` | Primary interactive flow (menu, watch mode, screenshots) |
| `ui.py` | Rich console helpers, panels, tables, masked display, formatting |

### Core Services Layer (`faaadmv/core/`)

| Component | Responsibility |
|-----------|----------------|
| `config.py` | Load, save, validate, encrypt/decrypt user configuration |
| `crypto.py` | Encryption primitives (Fernet, scrypt key derivation) |
| `keychain.py` | OS keychain wrapper for payment credentials (via `keyring`) |
| `browser.py` | Playwright browser lifecycle, context management, screenshots |
| `captcha.py` | CAPTCHA detection, API solving, manual fallback |

### Provider Layer (`faaadmv/providers/`)

| Component | Responsibility |
|-----------|----------------|
| `base.py` | Abstract base class defining provider interface |
| `ca_dmv.py` | California DMV portal automation |
| `registry.py` | Provider discovery and instantiation |

## Data Flow

### Registration Flow
```
User Input → Validation (Pydantic) → Encryption (Fernet) → Storage (File + Keyring)
```

### Status Check Flow
```
Load Config → Launch Browser → Navigate to DMV → Extract Data → Display Results
```

### Renewal Flow
```
Load Config → Launch Browser → Navigate → Fill Forms → CAPTCHA →
Eligibility Check → Display Fees → User Confirmation → Payment →
Capture Receipt → Save PDF
```

## Concurrency Model

- **Async/await** throughout for non-blocking I/O
- Playwright async API for browser operations
- Single browser context per command execution
- No concurrent DMV requests (rate limiting protection)

## State Management

The application is stateless between invocations. Persistent state is stored locally:

1. **Config file** (via `platformdirs`) — macOS default: `~/Library/Application Support/faaadmv/config.toml`
2. **OS Keychain** — payment credentials (CC, CVV)
3. **Artifacts** — screenshots in `~/Library/Application Support/faaadmv/artifacts/`

### Vehicle Resolution

When a command needs a vehicle, it resolves in this order:

```
--plate flag provided?
  └─ Yes → Use that vehicle (error if not found)
  └─ No  → How many vehicles registered?
              └─ 0 → Error: "Run faaadmv register first"
              └─ 1 → Use the only vehicle
              └─ 2+ → Is there a default?
                        └─ Yes → Use default
                        └─ No  → Interactive picker prompt
```

## Security Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                    User's Machine (Trusted)                  │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │ Config (local)  │  │ OS Keychain                     │   │
│  │ (platformdirs)  │  │ (CC, CVV)                       │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
│                              │                               │
│  ┌───────────────────────────┼───────────────────────────┐  │
│  │              Playwright Browser Sandbox               │  │
│  │                           │                           │  │
│  └───────────────────────────┼───────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    DMV Portal (Untrusted)                   │
└─────────────────────────────────────────────────────────────┘
```

## Extensibility Points

1. **New States**: Implement `BaseProvider` subclass
2. **New CAPTCHA Solvers**: Add solver to `captcha.py` strategy chain
3. **Custom UI Themes**: Extend Rich theme in `ui.py`
