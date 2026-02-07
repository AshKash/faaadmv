# faaadmv Testing Strategy

## Overview

Testing is critical for faaadmv because:
1. We're handling sensitive payment data
2. We're automating a real government website
3. Failures can cost users money or leave renewals incomplete

## Test Pyramid

```
                    ┌───────────────────┐
                    │   E2E Tests       │  ← Few, slow, real browser
                    │   (Playwright)    │
                    └───────────────────┘
               ┌─────────────────────────────┐
               │   Integration Tests         │  ← Mock DMV responses
               │   (pytest + httpx)          │
               └─────────────────────────────┘
          ┌───────────────────────────────────────┐
          │   Unit Tests                          │  ← Fast, isolated
          │   (pytest)                            │
          └───────────────────────────────────────┘
```

## Test Categories

### 1. Unit Tests

Test individual components in isolation.

```python
# tests/unit/test_models.py

import pytest
from pydantic import ValidationError
from faaadmv.models import VehicleInfo, PaymentInfo


class TestVehicleInfo:
    def test_valid_vehicle(self):
        vehicle = VehicleInfo(plate="8ABC123", vin_last5="12345")
        assert vehicle.plate == "8ABC123"
        assert vehicle.vin_last5 == "12345"

    def test_plate_normalization(self):
        vehicle = VehicleInfo(plate="8-abc-123", vin_last5="12345")
        assert vehicle.plate == "8ABC123"  # Normalized

    def test_invalid_vin_length(self):
        with pytest.raises(ValidationError) as exc:
            VehicleInfo(plate="8ABC123", vin_last5="1234")  # Too short
        assert "vin_last5" in str(exc.value)

    def test_invalid_vin_characters(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="8ABC123", vin_last5="12O45")  # O not allowed


class TestPaymentInfo:
    def test_valid_card(self):
        payment = PaymentInfo(
            card_number="4242424242424242",
            expiry_month=12,
            expiry_year=2027,
            cvv="123",
            billing_zip="90001",
        )
        assert payment.masked_number == "****4242"

    def test_luhn_validation(self):
        with pytest.raises(ValidationError) as exc:
            PaymentInfo(
                card_number="1234567890123456",  # Invalid Luhn
                expiry_month=12,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )
        assert "Luhn" in str(exc.value)

    def test_expired_card(self):
        payment = PaymentInfo(
            card_number="4242424242424242",
            expiry_month=1,
            expiry_year=2020,  # Past
            cvv="123",
            billing_zip="90001",
        )
        assert payment.is_expired is True
```

```python
# tests/unit/test_crypto.py

import pytest
from faaadmv.core.crypto import ConfigCrypto


class TestConfigCrypto:
    def test_encrypt_decrypt_roundtrip(self):
        crypto = ConfigCrypto("test-passphrase")
        plaintext = "sensitive data here"

        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)

        assert decrypted == plaintext

    def test_different_passphrases(self):
        crypto1 = ConfigCrypto("passphrase-1")
        crypto2 = ConfigCrypto("passphrase-2")

        encrypted = crypto1.encrypt("secret")

        with pytest.raises(Exception):  # Fernet InvalidToken
            crypto2.decrypt(encrypted)

    def test_salt_uniqueness(self):
        crypto = ConfigCrypto("same-passphrase")

        enc1 = crypto.encrypt("same data")
        enc2 = crypto.encrypt("same data")

        # Different salts = different ciphertext
        assert enc1 != enc2

    def test_empty_passphrase_rejected(self):
        with pytest.raises(ValueError):
            ConfigCrypto("")
```

### 2. Integration Tests

Test component interactions with mocked external services.

```python
# tests/integration/test_config_manager.py

import pytest
from pathlib import Path
from faaadmv.core.config import ConfigManager
from faaadmv.models import UserConfig, VehicleInfo, OwnerInfo, Address


@pytest.fixture
def temp_config_dir(tmp_path):
    return tmp_path / ".config" / "faaadmv"


@pytest.fixture
def sample_config():
    return UserConfig(
        vehicle=VehicleInfo(plate="8ABC123", vin_last5="12345"),
        owner=OwnerInfo(
            full_name="Jane Doe",
            phone="5551234567",
            email="jane@example.com",
            address=Address(
                street="123 Main St",
                city="Los Angeles",
                state="CA",
                zip_code="90001",
            ),
        ),
    )


class TestConfigManager:
    def test_save_and_load(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="test123")

        loaded = manager.load(passphrase="test123")

        assert loaded.vehicle.plate == sample_config.vehicle.plate
        assert loaded.owner.full_name == sample_config.owner.full_name

    def test_config_file_encrypted(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="test123")

        config_file = temp_config_dir / "config.enc"
        contents = config_file.read_bytes()

        # Should not contain plaintext
        assert b"Jane Doe" not in contents
        assert b"8ABC123" not in contents

    def test_wrong_passphrase(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="correct")

        with pytest.raises(ConfigDecryptionError):
            manager.load(passphrase="wrong")

    def test_config_not_found(self, temp_config_dir):
        manager = ConfigManager(config_dir=temp_config_dir)

        with pytest.raises(ConfigNotFoundError):
            manager.load(passphrase="any")
```

```python
# tests/integration/test_provider_mock.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from faaadmv.providers.ca_dmv import CADMVProvider
from faaadmv.models import StatusType


@pytest.fixture
def mock_page():
    page = AsyncMock()
    page.goto = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.query_selector = AsyncMock(return_value=None)
    return page


@pytest.fixture
def mock_context(mock_page):
    context = AsyncMock()
    context.new_page = AsyncMock(return_value=mock_page)
    return context


class TestCADMVProviderMocked:
    @pytest.mark.asyncio
    async def test_status_check_success(self, mock_context, mock_page):
        # Set up mock responses
        mock_page.query_selector.side_effect = [
            None,  # No error
            MagicMock(inner_text=AsyncMock(return_value="2019 Honda Accord")),
            MagicMock(inner_text=AsyncMock(return_value="06/20/2026")),
            MagicMock(inner_text=AsyncMock(return_value="Current")),
        ]

        provider = CADMVProvider(mock_context)
        await provider.initialize()

        status = await provider.get_registration_status("8ABC123", "12345")

        assert status.plate == "8ABC123"
        assert status.status == StatusType.CURRENT

    @pytest.mark.asyncio
    async def test_status_check_vehicle_not_found(self, mock_context, mock_page):
        error_el = MagicMock()
        error_el.inner_text = AsyncMock(return_value="Vehicle not found")
        mock_page.query_selector.return_value = error_el

        provider = CADMVProvider(mock_context)
        await provider.initialize()

        with pytest.raises(VehicleNotFoundError):
            await provider.get_registration_status("INVALID", "00000")
```

### 3. E2E Tests

Test against real browser with recorded/mocked DMV responses.

```python
# tests/e2e/test_cli_flows.py

import pytest
from typer.testing import CliRunner
from faaadmv.cli.app import app


runner = CliRunner()


class TestRegisterCommand:
    def test_register_interactive(self):
        result = runner.invoke(
            app,
            ["register"],
            input="\n".join([
                "8ABC123",      # plate
                "12345",        # vin
                "Jane Doe",     # name
                "5551234567",   # phone
                "jane@test.com",# email
                "123 Main St",  # street
                "Los Angeles",  # city
                "CA",           # state
                "90001",        # zip
                "4242424242424242",  # card
                "12",           # exp month
                "27",           # exp year
                "123",          # cvv
                "90001",        # billing zip
                "testpass",     # passphrase
                "testpass",     # confirm passphrase
            ]),
        )

        assert result.exit_code == 0
        assert "Configuration saved" in result.output

    def test_register_verify(self, configured_app):
        result = runner.invoke(
            app,
            ["register", "--verify"],
            input="testpass\n",
        )

        assert result.exit_code == 0
        assert "****4242" in result.output  # Masked card
        assert "Jane Doe" in result.output


class TestStatusCommand:
    @pytest.mark.vcr()  # Record/replay HTTP
    def test_status_check(self, configured_app):
        result = runner.invoke(
            app,
            ["status"],
            input="testpass\n",
        )

        assert result.exit_code == 0
        assert "8ABC123" in result.output
        assert "Status:" in result.output


class TestRenewCommand:
    def test_renew_dry_run(self, configured_app):
        result = runner.invoke(
            app,
            ["renew", "--dry-run"],
            input="testpass\n",
        )

        assert result.exit_code == 0
        assert "Dry run complete" in result.output
        assert "Payment" not in result.output  # Should stop before payment

    def test_renew_user_cancels(self, configured_app):
        result = runner.invoke(
            app,
            ["renew"],
            input="testpass\nn\n",  # Decline payment confirmation
        )

        assert result.exit_code == 0
        assert "Aborted" in result.output
```

### 4. Browser Tests with Playwright

Test actual browser automation against recorded responses.

```python
# tests/browser/test_ca_dmv_real.py

import pytest
from playwright.async_api import async_playwright
from faaadmv.providers.ca_dmv import CADMVProvider


@pytest.fixture
async def browser_context():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        yield context
        await browser.close()


class TestCADMVBrowser:
    @pytest.mark.asyncio
    @pytest.mark.browser
    @pytest.mark.skipif(
        not os.getenv("RUN_BROWSER_TESTS"),
        reason="Browser tests disabled"
    )
    async def test_navigation_to_status_page(self, browser_context):
        provider = CADMVProvider(browser_context)
        await provider.initialize()

        await provider.page.goto(provider.STATUS_URL)
        await provider.wait_for_navigation()

        # Verify page loaded
        title = await provider.page.title()
        assert "DMV" in title

        await provider.cleanup()
```

## Test Fixtures

```python
# tests/conftest.py

import pytest
from pathlib import Path
import tempfile
import shutil


@pytest.fixture
def temp_home(tmp_path, monkeypatch):
    """Provide isolated home directory for tests."""
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    return fake_home


@pytest.fixture
def configured_app(temp_home):
    """App with pre-configured test data."""
    config_dir = temp_home / ".config" / "faaadmv"
    config_dir.mkdir(parents=True)

    # Copy test fixtures
    fixtures = Path(__file__).parent / "fixtures"
    shutil.copy(fixtures / "config.enc", config_dir / "config.enc")

    return config_dir


@pytest.fixture
def mock_keyring(monkeypatch):
    """Mock keyring for payment data."""
    storage = {}

    def mock_get(service, key):
        return storage.get(f"{service}:{key}")

    def mock_set(service, key, value):
        storage[f"{service}:{key}"] = value

    def mock_delete(service, key):
        storage.pop(f"{service}:{key}", None)

    monkeypatch.setattr("keyring.get_password", mock_get)
    monkeypatch.setattr("keyring.set_password", mock_set)
    monkeypatch.setattr("keyring.delete_password", mock_delete)

    return storage
```

## Test Data

```python
# tests/fixtures/test_data.py

# Valid test card numbers (Luhn-valid, not real cards)
TEST_CARDS = {
    "visa": "4242424242424242",
    "mastercard": "5555555555554444",
    "amex": "378282246310005",
}

# Test vehicles
TEST_VEHICLES = {
    "valid": {"plate": "8ABC123", "vin_last5": "12345"},
    "expired": {"plate": "7XYZ999", "vin_last5": "99999"},
    "not_found": {"plate": "0000000", "vin_last5": "00000"},
}
```

## Running Tests

```bash
# All tests
pytest

# Unit tests only (fast)
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# With coverage
pytest --cov=faaadmv --cov-report=html

# Browser tests (slow, requires DISPLAY)
RUN_BROWSER_TESTS=1 pytest tests/browser -v

# Specific test
pytest tests/unit/test_models.py::TestPaymentInfo -v
```

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

## Test Coverage Goals

| Component | Target |
|-----------|--------|
| Models | 95% |
| Crypto | 100% |
| Config | 90% |
| CLI | 80% |
| Providers | 70% (mocked) |
| Overall | 85% |
