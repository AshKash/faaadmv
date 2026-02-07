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
│       ├── py.typed               # PEP 561 marker
│       │
│       ├── cli/                   # CLI layer
│       │   ├── __init__.py
│       │   ├── app.py             # Typer application
│       │   ├── commands/          # Command implementations
│       │   │   ├── __init__.py
│       │   │   ├── register.py    # faaadmv register
│       │   │   ├── status.py      # faaadmv status
│       │   │   └── renew.py       # faaadmv renew
│       │   ├── ui.py              # Rich console helpers
│       │   └── prompts.py         # Interactive prompts
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
│   ├── conftest.py                # Pytest fixtures
│   ├── fixtures/                  # Test data files
│   │   ├── config.enc             # Sample encrypted config
│   │   └── test_data.py           # Test constants
│   ├── unit/                      # Unit tests
│   │   ├── test_models.py
│   │   ├── test_crypto.py
│   │   └── test_validators.py
│   ├── integration/               # Integration tests
│   │   ├── test_config_manager.py
│   │   └── test_provider_mock.py
│   ├── e2e/                       # End-to-end tests
│   │   └── test_cli_flows.py
│   └── browser/                   # Browser tests
│       └── test_ca_dmv_real.py
│
├── scripts/                       # Development scripts
│   ├── lint.sh                    # Run linters
│   ├── test.sh                    # Run tests
│   └── release.sh                 # Build and publish
│
├── .github/
│   └── workflows/
│       ├── test.yml               # CI tests
│       └── release.yml            # PyPI publishing
│
├── PRD.md                         # Product requirements
├── README.md                      # Project readme
├── LICENSE                        # MIT license
├── pyproject.toml                 # Project configuration
├── .gitignore                     # Git ignore rules
└── .pre-commit-config.yaml        # Pre-commit hooks
```

## Key Files

### pyproject.toml

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "faaadmv"
version = "0.1.0"
description = "Agentic DMV registration renewal CLI"
readme = "README.md"
license = "MIT"
requires-python = ">=3.11"
authors = [
    { name = "Your Name", email = "you@example.com" }
]
keywords = ["dmv", "cli", "automation", "playwright"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pydantic>=2.0.0",
    "pydantic[email]",
    "playwright>=1.40.0",
    "cryptography>=41.0.0",
    "keyring>=24.0.0",
    "platformdirs>=4.0.0",
    "tomli>=2.0.0",
    "tomli-w>=1.0.0",
    "httpx>=0.25.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0",
    "pre-commit>=3.5.0",
]

[project.scripts]
faaadmv = "faaadmv.cli.app:main"

[project.urls]
Homepage = "https://github.com/yourusername/faaadmv"
Repository = "https://github.com/yourusername/faaadmv"
Issues = "https://github.com/yourusername/faaadmv/issues"

[tool.hatch.build.targets.wheel]
packages = ["src/faaadmv"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
addopts = "-v --tb=short"
```

### src/faaadmv/__init__.py

```python
"""faaadmv - Agentic DMV registration renewal CLI."""

__version__ = "0.1.0"
__author__ = "Your Name"
```

### src/faaadmv/__main__.py

```python
"""Entry point for python -m faaadmv."""

from faaadmv.cli.app import main

if __name__ == "__main__":
    main()
```

### src/faaadmv/cli/app.py

```python
"""Main CLI application."""

import typer
from rich.console import Console

from faaadmv import __version__
from faaadmv.cli.commands import register, status, renew

app = typer.Typer(
    name="faaadmv",
    help="Agentic DMV registration renewal CLI",
    no_args_is_help=True,
    rich_markup_mode="rich",
)

console = Console()

# Register commands
app.add_typer(register.app, name="register")
app.command()(status.status)
app.command()(renew.renew)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False, "--version", "-V", help="Show version"
    ),
) -> None:
    """faaadmv - Renew your vehicle registration from the command line."""
    if version:
        console.print(f"faaadmv v{__version__}")
        raise typer.Exit()


if __name__ == "__main__":
    app()
```

### .gitignore

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.env
.venv
env/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo
*~

# Testing
.coverage
htmlcov/
.pytest_cache/
.mypy_cache/

# Project specific
*.enc
*.pdf
dmv_receipt_*.pdf

# OS
.DS_Store
Thumbs.db
```

### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.0
    hooks:
      - id: mypy
        additional_dependencies:
          - pydantic>=2.0
          - typer>=0.9

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `cli/app.py` | Typer app setup, command routing |
| `cli/commands/*.py` | Individual command implementations |
| `cli/ui.py` | Rich tables, panels, progress bars |
| `cli/prompts.py` | Interactive input with validation |
| `core/config.py` | Load/save encrypted config |
| `core/crypto.py` | Fernet encryption, key derivation |
| `core/keychain.py` | OS keychain abstraction |
| `core/browser.py` | Playwright lifecycle management |
| `core/captcha.py` | CAPTCHA detection and solving |
| `providers/base.py` | Abstract provider interface |
| `providers/ca_dmv.py` | CA-specific implementation |
| `models/*.py` | Pydantic data models |
| `exceptions.py` | Custom exception classes |

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
