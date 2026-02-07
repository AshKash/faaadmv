# faaadmv Project Structure

## Directory Layout

```
faaadmv/
├── docs/                          # Documentation
│   ├── ARCHITECTURE.md            # System architecture
│   ├── DATA_MODELS.md             # Pydantic models
│   ├── SECURITY.md                # Security design
│   ├── PROVIDERS.md               # Provider interface
│   ├── TESTING.md                 # Testing strategy
│   └── PROJECT_STRUCTURE.md       # This file
│
├── src/
│   └── faaadmv/                   # Main package
│       ├── __init__.py            # Package init, version
│       ├── __main__.py            # Entry point: python -m faaadmv
│       │
│       ├── cli/                   # CLI layer
│       │   ├── __init__.py
│       │   ├── app.py             # Typer application + command definitions
│       │   ├── commands/          # Command implementations
│       │   │   ├── __init__.py
│       │   │   ├── register.py    # faaadmv register
│       │   │   ├── status.py      # faaadmv status
│       │   │   └── renew.py       # faaadmv renew
│       │   └── ui.py              # Rich console helpers
│       │
│       ├── core/                  # Core services
│       │   ├── __init__.py
│       │   ├── config.py          # ConfigManager
│       │   ├── crypto.py          # Encryption utilities
│       │   ├── keychain.py        # OS keychain wrapper
│       │   ├── browser.py         # Playwright wrapper
│       │   └── captcha.py         # CAPTCHA handling
│       │
│       ├── providers/             # State providers
│       │   ├── __init__.py
│       │   ├── base.py            # BaseProvider ABC
│       │   ├── registry.py        # Provider discovery
│       │   └── ca_dmv.py          # California implementation
│       │
│       ├── models/                # Data models
│       │   ├── __init__.py        # Re-exports
│       │   ├── vehicle.py         # VehicleInfo
│       │   ├── owner.py           # OwnerInfo, Address
│       │   ├── payment.py         # PaymentInfo
│       │   ├── config.py          # UserConfig
│       │   └── results.py         # Status, Eligibility, etc.
│       │
│       └── exceptions.py          # Custom exceptions
│
├── tests/                         # Test suite
│   ├── __init__.py
│   ├── conftest.py                # Shared pytest fixtures
│   ├── unit/                      # Unit tests
│   │   ├── test_models_vehicle.py
│   │   ├── test_models_owner.py
│   │   ├── test_models_payment.py
│   │   ├── test_models_config.py
│   │   ├── test_models_results.py
│   │   ├── test_crypto.py
│   │   ├── test_config_manager.py
│   │   ├── test_exceptions.py
│   │   ├── test_ui.py
│   │   ├── test_registry.py
│   │   └── test_ca_dmv_parsing.py
│   ├── integration/               # Integration tests
│   │   ├── test_cli_app.py
│   │   ├── test_config_roundtrip.py
│   │   └── test_keychain.py
│   └── e2e/                       # End-to-end tests
│       ├── test_register_flow.py
│       └── test_status_renew_flow.py
│
├── testing/                       # Test agent tracking files
│   ├── TEST_STATUS.md             # Test results and coverage
│   └── BUGS.md                    # Bug reports with repro steps
│
├── CLAUDE.md                      # Agent entry point (read this first)
├── PRD.md                         # Product requirements
├── README.md                      # Project readme
├── STATUS.md                      # Feature implementation status
├── pyproject.toml                 # Project configuration
└── .gitignore                     # Git ignore rules
```

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `cli/app.py` | Typer app setup, command definitions with options |
| `cli/commands/*.py` | Individual command implementations (register, status, renew) |
| `cli/ui.py` | Rich panels, tables, masked display, phone formatting |
| `core/config.py` | Load, save, validate, encrypt/decrypt user configuration |
| `core/crypto.py` | Fernet encryption, scrypt key derivation |
| `core/keychain.py` | OS keychain abstraction for payment credentials |
| `core/browser.py` | Playwright lifecycle, tracker blocking, context management |
| `core/captcha.py` | CAPTCHA detection, API solving, manual fallback |
| `providers/base.py` | Abstract provider interface (5 abstract methods) |
| `providers/ca_dmv.py` | CA DMV portal automation and prose parsing |
| `providers/registry.py` | Provider discovery (`get_provider("CA")`) |
| `models/*.py` | Pydantic v2 data models with field validators |
| `exceptions.py` | Custom exception hierarchy (all inherit `FaaadmvError`) |

## Import Conventions

```python
# Absolute imports only
from faaadmv.models import UserConfig, VehicleInfo
from faaadmv.core.config import ConfigManager
from faaadmv.providers import get_provider

# Type imports
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from playwright.async_api import Page
```
