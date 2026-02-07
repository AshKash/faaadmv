# faaadmv Testing Strategy

## Overview

Testing is critical for faaadmv because:
1. We're handling sensitive payment data
2. We're automating a real government website
3. Failures can cost users money or leave renewals incomplete

## Test Pyramid

```
                    +-------------------+
                    |   E2E Tests       |  <- Few, CLI flows via CliRunner
                    |   (pytest+typer)  |
                    +-------------------+
               +-----------------------------+
               |   Integration Tests         |  <- Component interactions
               |   (pytest + mocks)          |
               +-----------------------------+
          +---------------------------------------+
          |   Unit Tests                          |  <- Fast, isolated
          |   (pytest)                            |
          +---------------------------------------+
```

## Test Categories

### 1. Unit Tests (`tests/unit/`)

Test individual components in isolation. Fast, no I/O.

| Test File | Component | Tests |
|-----------|-----------|-------|
| `test_models_vehicle.py` | VehicleInfo validation | 13 |
| `test_models_owner.py` | OwnerInfo + Address validation | 18 |
| `test_models_payment.py` | PaymentInfo, Luhn, masking | 20 |
| `test_models_config.py` | UserConfig serialization | 8 |
| `test_models_results.py` | RegistrationStatus, FeeBreakdown, RenewalResult | 19 |
| `test_crypto.py` | ConfigCrypto encrypt/decrypt | 11 |
| `test_config_manager.py` | ConfigManager save/load/delete | 11 |
| `test_exceptions.py` | Exception hierarchy and messages | 20 |
| `test_ui.py` | Rich panel helpers, masking, formatting | 15 |
| `test_registry.py` | Provider registry lookup | 10 |
| `test_ca_dmv_parsing.py` | CA DMV prose parsing, date/amount extraction | 34 |

### 2. Integration Tests (`tests/integration/`)

Test component interactions with mocked external services.

| Test File | Component | Tests |
|-----------|-----------|-------|
| `test_cli_app.py` | CLI entry points, command routing | 16 |
| `test_config_roundtrip.py` | Config encrypt -> save -> load -> decrypt | 4 |
| `test_keychain.py` | Payment keychain store/retrieve/delete | 8 |

### 3. E2E Tests (`tests/e2e/`)

Test full CLI command flows using `typer.testing.CliRunner`.

| Test File | Component | Tests |
|-----------|-----------|-------|
| `test_register_flow.py` | Register, verify, reset, wrong passphrase | 4 |
| `test_status_renew_flow.py` | Status, renew (dry-run, full, decline), prose display | 11 |

## Test Fixtures (`tests/conftest.py`)

Key shared fixtures:

- `temp_home(tmp_path, monkeypatch)` -- Isolated HOME directory
- `saved_config(temp_home)` -- Pre-saved encrypted config + payment in mock keyring
- `mock_keyring(monkeypatch)` -- In-memory keyring replacement

E2E tests mock the provider layer to avoid real browser/network calls while testing the full CLI pipeline.

## Running Tests

```bash
# All tests
pytest

# Unit tests only (fast, ~2s)
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# E2E tests
pytest tests/e2e -v

# With coverage
pytest --cov=faaadmv --cov-report=html

# Specific test file
pytest tests/unit/test_ca_dmv_parsing.py -v

# Specific test class
pytest tests/unit/test_models_results.py::TestRegistrationStatus -v
```

## Test Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| Models | 95% | 92-100% |
| Crypto | 100% | 100% |
| Config | 90% | 87% |
| CLI | 80% | 60-93% |
| Providers | 70% | 95% (parsing) |
| Overall | 85% | ~85% |

## CI Configuration

```yaml
# .github/workflows/test.yml

name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Install dependencies
        run: |
          uv pip install -e ".[dev]"
          playwright install chromium

      - name: Run unit tests
        run: pytest tests/unit -v --cov=faaadmv

      - name: Run integration tests
        run: pytest tests/integration -v

      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

## Multi-Agent Testing Protocol

This project uses a test agent (separate from the dev agent). See:
- `testing/TEST_STATUS.md` -- Test results, coverage, run history
- `testing/BUGS.md` -- Bug reports with repro steps and severity
- `STATUS.md` -- Feature status (dev agent marks features `testable`)
