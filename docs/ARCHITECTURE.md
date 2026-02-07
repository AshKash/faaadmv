# faaadmv System Architecture

## Overview

faaadmv is a layered CLI application that automates DMV vehicle registration renewal through browser automation.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           CLI Layer (Typer + Rich)                      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │ register │ │ vehicles │ │  status  │ │  renew   │ │   help   │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           Core Services Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────────┐ │
│  │ ConfigManager   │  │ BrowserManager  │  │ CaptchaSolver           │ │
│  │ - load/save     │  │ - launch        │  │ - detect                │ │
│  │ - encrypt       │  │ - navigate      │  │ - solve (API/manual)    │ │
│  │ - validate      │  │ - screenshot    │  │                         │ │
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
| `ui.py` | Rich console helpers, prompts, tables, progress indicators |
| `prompts.py` | Interactive input collection with validation feedback |

### Core Services Layer (`faaadmv/core/`)

| Component | Responsibility |
|-----------|----------------|
| `config.py` | Load, save, validate, encrypt/decrypt user configuration |
| `crypto.py` | Encryption primitives (Fernet, key derivation) |
| `browser.py` | Playwright browser lifecycle, context management |
| `captcha.py` | CAPTCHA detection, API solving, manual fallback |
| `exceptions.py` | Custom exception hierarchy |

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

## Error Handling Strategy

```
Exception Hierarchy:
├── FaaadmvError (base)
│   ├── ConfigError
│   │   ├── ConfigNotFoundError
│   │   ├── ConfigDecryptionError
│   │   └── ConfigValidationError
│   ├── BrowserError
│   │   ├── NavigationError
│   │   ├── TimeoutError
│   │   └── SelectorNotFoundError
│   ├── DMVError
│   │   ├── EligibilityError
│   │   ├── SmogCheckError
│   │   ├── InsuranceError
│   │   └── PaymentError
│   └── CaptchaError
│       ├── CaptchaDetectedError
│       └── CaptchaSolveFailedError
```

## State Management

The application is **stateless between invocations**. All persistent state is stored in:

1. **Config file** (`~/.config/faaadmv/config.enc`) - Encrypted user data (owner, vehicles)
2. **OS Keychain** - Payment credentials (CC, CVV)
3. **Browser context** - Session cookies (ephemeral, per-run)

### Vehicle Resolution (planned — multi-vehicle)

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
│  │ Config (enc)    │  │ OS Keychain                     │   │
│  │ ~/.config/      │  │ (CC, CVV)                       │   │
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
2. **New Vehicles**: Add/remove via `faaadmv vehicles` (planned)
3. **New CAPTCHA Solvers**: Add solver to `captcha.py` strategy chain
4. **New Storage Backends**: Implement `ConfigBackend` protocol
5. **Custom UI Themes**: Extend Rich theme in `ui.py`
