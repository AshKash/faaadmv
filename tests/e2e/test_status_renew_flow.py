"""E2E test: status and renew commands with mocked browser.

Tests the full flow from config load → browser → provider → display.
Browser/provider layer is mocked since we can't hit real DMV in tests.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from typer.testing import CliRunner

from faaadmv.cli.app import app
from faaadmv.core.config import ConfigManager
from faaadmv.models import (
    EligibilityResult,
    FeeBreakdown,
    FeeItem,
    InsuranceStatus,
    RegistrationStatus,
    RenewalResult,
    SmogStatus,
    StatusType,
)
from faaadmv.models.config import UserConfig
from faaadmv.models.owner import Address, OwnerInfo
from faaadmv.models.payment import PaymentInfo
from faaadmv.models.vehicle import VehicleEntry, VehicleInfo

runner = CliRunner()


@pytest.fixture
def saved_config(tmp_path):
    """Create a real saved config on disk for testing."""
    config_dir = tmp_path / ".config" / "faaadmv"
    config_dir.mkdir(parents=True)
    manager = ConfigManager(config_dir=config_dir)

    config = UserConfig(
        vehicles=[VehicleEntry(
            vehicle=VehicleInfo(plate="8ABC123", vin_last5="12345"),
            is_default=True,
        )],
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
    manager.save(config, passphrase="testpass")
    return manager


@pytest.fixture
def mock_status_result():
    """Typical successful status response."""
    return RegistrationStatus(
        plate="8ABC123",
        vin_last5="12345",
        vehicle_description="2019 Honda Accord",
        expiration_date=date(2026, 6, 20),
        status=StatusType.CURRENT,
        days_until_expiry=133,
        status_message="An application for Vehicle Registration 8ABC123 is in progress as of February 07, 2026.\nYour registration has not yet been mailed. No further action is required.",
        last_updated=date(2026, 2, 7),
    )


@pytest.fixture
def mock_eligibility():
    return EligibilityResult(
        eligible=True,
        smog=SmogStatus(passed=True, check_date=date(2026, 1, 15)),
        insurance=InsuranceStatus(verified=True, provider="State Farm"),
    )


@pytest.fixture
def mock_fees():
    return FeeBreakdown(items=[
        FeeItem(description="Registration Fee", amount=Decimal("168.00")),
        FeeItem(description="CHP Fee", amount=Decimal("32.00")),
        FeeItem(description="County Fee", amount=Decimal("48.00")),
    ])


@pytest.fixture
def mock_renewal_result():
    return RenewalResult(
        success=True,
        confirmation_number="CONF-12345",
        new_expiration_date=date(2027, 2, 1),
        amount_paid=Decimal("248.00"),
        receipt_path="./dmv_receipt_2026-02-07.pdf",
    )


def _make_mock_provider(status_result, eligibility=None, fees=None, renewal_result=None):
    """Build a mock provider that returns given results."""
    provider = AsyncMock()
    provider.get_registration_status = AsyncMock(return_value=status_result)
    provider.validate_eligibility = AsyncMock(return_value=eligibility)
    provider.get_fee_breakdown = AsyncMock(return_value=fees)
    provider.submit_renewal = AsyncMock(return_value=renewal_result)
    provider.has_captcha = AsyncMock(return_value=False)
    provider.initialize = AsyncMock()
    provider.cleanup = AsyncMock()
    return provider


def _make_mock_browser_manager():
    """Build a mock BrowserManager that works as async context manager."""
    bm = AsyncMock()
    bm.context = MagicMock()
    bm.__aenter__ = AsyncMock(return_value=bm)
    bm.__aexit__ = AsyncMock(return_value=None)
    return bm


class TestStatusFlow:
    """P0: Can a user check registration status?"""

    def test_status_happy_path(self, saved_config, mock_status_result):
        """register → status shows real status from DMV."""
        mock_provider = _make_mock_provider(mock_status_result)
        mock_bm = _make_mock_browser_manager()

        # Mock provider class to return our mock instance
        mock_provider_cls = MagicMock(return_value=mock_provider)

        with (
            patch("faaadmv.cli.commands.status.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.status.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.status.get_provider", return_value=mock_provider_cls),
        ):
            result = runner.invoke(
                app,
                ["status"],
                input="testpass\n",
            )

        print("STATUS OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Status failed: {result.output}"
        assert "8ABC123" in result.output
        assert "2019 Honda Accord" in result.output
        assert "Current" in result.output

    def test_status_wrong_passphrase(self, saved_config):
        """Status with wrong passphrase → clear error, no crash."""
        with patch("faaadmv.cli.commands.status.ConfigManager", return_value=saved_config):
            result = runner.invoke(
                app,
                ["status"],
                input="wrongpass\n",
            )

        assert result.exit_code == 1
        assert "Wrong passphrase" in result.output or "passphrase" in result.output.lower()


class TestRenewDryRunFlow:
    """P0: Can a user do a dry run of renewal?"""

    def test_renew_dry_run_happy_path(self, saved_config, mock_keyring, mock_eligibility, mock_fees):
        """register → renew --dry-run shows eligibility + fees, stops before payment."""
        mock_provider = _make_mock_provider(
            status_result=None,
            eligibility=mock_eligibility,
            fees=mock_fees,
        )
        mock_bm = _make_mock_browser_manager()
        mock_provider_cls = MagicMock(return_value=mock_provider)

        with (
            patch("faaadmv.cli.commands.renew.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.renew.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.renew.get_provider", return_value=mock_provider_cls),
            patch("faaadmv.cli.commands.renew.PaymentKeychain") as MockKC,
        ):
            MockKC.retrieve.return_value = None  # No payment needed for dry run

            result = runner.invoke(
                app,
                ["renew", "--dry-run"],
                input="testpass\n",
            )

        print("DRY RUN OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Dry run failed: {result.output}"
        assert "Smog" in result.output
        assert "Insurance" in result.output
        assert "$248.00" in result.output
        assert "Dry run complete" in result.output


class TestRenewFullFlow:
    """P1: Can a user complete a full renewal with payment?"""

    def test_renew_full_happy_path(
        self, saved_config, mock_keyring,
        mock_eligibility, mock_fees, mock_renewal_result,
    ):
        """register → renew → confirm payment → success."""
        mock_provider = _make_mock_provider(
            status_result=None,
            eligibility=mock_eligibility,
            fees=mock_fees,
            renewal_result=mock_renewal_result,
        )
        mock_bm = _make_mock_browser_manager()
        mock_provider_cls = MagicMock(return_value=mock_provider)

        payment = PaymentInfo(
            card_number="4242424242424242",
            expiry_month=12,
            expiry_year=2027,
            cvv="123",
            billing_zip="90001",
        )

        with (
            patch("faaadmv.cli.commands.renew.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.renew.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.renew.get_provider", return_value=mock_provider_cls),
            patch("faaadmv.cli.commands.renew.PaymentKeychain") as MockKC,
        ):
            MockKC.retrieve.return_value = payment

            result = runner.invoke(
                app,
                ["renew"],
                input="testpass\ny\n",  # passphrase + confirm payment
            )

        print("RENEW OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Renew failed: {result.output}"
        assert "Payment successful" in result.output
        assert "CONF-12345" in result.output
        assert "February 2027" in result.output

    def test_renew_user_declines_payment(
        self, saved_config, mock_keyring,
        mock_eligibility, mock_fees,
    ):
        """User sees fees but declines → no payment made."""
        mock_provider = _make_mock_provider(
            status_result=None,
            eligibility=mock_eligibility,
            fees=mock_fees,
        )
        mock_bm = _make_mock_browser_manager()
        mock_provider_cls = MagicMock(return_value=mock_provider)

        payment = PaymentInfo(
            card_number="4242424242424242",
            expiry_month=12,
            expiry_year=2027,
            cvv="123",
            billing_zip="90001",
        )

        with (
            patch("faaadmv.cli.commands.renew.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.renew.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.renew.get_provider", return_value=mock_provider_cls),
            patch("faaadmv.cli.commands.renew.PaymentKeychain") as MockKC,
        ):
            MockKC.retrieve.return_value = payment

            result = runner.invoke(
                app,
                ["renew"],
                input="testpass\nn\n",  # passphrase + decline payment
            )

        print("DECLINE OUTPUT:", result.output)
        assert result.exit_code == 0
        assert "Aborted" in result.output or "No payment" in result.output

        # Confirm submit_renewal was never called
        mock_provider.submit_renewal.assert_not_called()

    def test_renew_no_payment_info(self, saved_config, mock_keyring):
        """Renew without payment info → clear error."""
        with (
            patch("faaadmv.cli.commands.renew.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.renew.PaymentKeychain") as MockKC,
        ):
            MockKC.retrieve.return_value = None

            result = runner.invoke(
                app,
                ["renew"],
                input="testpass\n",
            )

        assert result.exit_code == 1
        assert "Payment" in result.output and "not found" in result.output.lower()

    def test_renew_expired_card(self, saved_config, mock_keyring):
        """P1: Renew with expired card → clear error before browser launch."""
        expired_payment = PaymentInfo(
            card_number="4242424242424242",
            expiry_month=1,
            expiry_year=2024,
            cvv="123",
            billing_zip="90001",
        )

        with (
            patch("faaadmv.cli.commands.renew.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.renew.PaymentKeychain") as MockKC,
        ):
            MockKC.retrieve.return_value = expired_payment

            result = runner.invoke(
                app,
                ["renew"],
                input="testpass\n",
            )

        print("EXPIRED CARD OUTPUT:", result.output)
        assert result.exit_code == 1
        assert "expired" in result.output.lower()


class TestStatusExpired:
    """P1: Status display for expired / expiring-soon registration."""

    def test_status_expired_registration(self, saved_config):
        """Status shows expired registration clearly."""
        expired_status = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            vehicle_description="2019 Honda Accord",
            expiration_date=date(2025, 1, 15),
            status=StatusType.EXPIRED,
            days_until_expiry=-388,
        )
        mock_provider = _make_mock_provider(expired_status)
        mock_bm = _make_mock_browser_manager()
        mock_provider_cls = MagicMock(return_value=mock_provider)

        with (
            patch("faaadmv.cli.commands.status.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.status.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.status.get_provider", return_value=mock_provider_cls),
        ):
            result = runner.invoke(
                app,
                ["status"],
                input="testpass\n",
            )

        print("EXPIRED STATUS OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Expired status failed: {result.output}"
        assert "Expired" in result.output
        assert "Overdue" in result.output or "388" in result.output

    def test_status_expiring_soon(self, saved_config):
        """Status shows expiring-soon warning."""
        expiring_status = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            vehicle_description="2019 Honda Accord",
            expiration_date=date(2026, 2, 28),
            status=StatusType.EXPIRING_SOON,
            days_until_expiry=21,
        )
        mock_provider = _make_mock_provider(expiring_status)
        mock_bm = _make_mock_browser_manager()
        mock_provider_cls = MagicMock(return_value=mock_provider)

        with (
            patch("faaadmv.cli.commands.status.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.status.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.status.get_provider", return_value=mock_provider_cls),
        ):
            result = runner.invoke(
                app,
                ["status"],
                input="testpass\n",
            )

        print("EXPIRING SOON OUTPUT:", result.output)
        assert result.exit_code == 0, f"Expiring soon status failed: {result.output}"
        assert "Expiring Soon" in result.output
        assert "21" in result.output


class TestStatusProseDisplay:
    """P0: Status display with prose-only DMV response (new CA DMV parsing)."""

    def test_status_with_message_and_last_updated(self, saved_config):
        """Status with status_message and last_updated renders both."""
        prose_status = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            status=StatusType.PENDING,
            status_message=(
                "An application for Vehicle Registration 8ABC123 is in progress "
                "as of February 07, 2026.\n"
                "Your registration has not yet been mailed. "
                "No further action is required."
            ),
            last_updated=date(2026, 2, 7),
        )
        mock_provider = _make_mock_provider(prose_status)
        mock_bm = _make_mock_browser_manager()
        mock_provider_cls = MagicMock(return_value=mock_provider)

        with (
            patch("faaadmv.cli.commands.status.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.status.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.status.get_provider", return_value=mock_provider_cls),
        ):
            result = runner.invoke(
                app,
                ["status"],
                input="testpass\n",
            )

        print("PROSE STATUS OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Prose status failed: {result.output}"
        assert "Pending" in result.output
        assert "8ABC123" in result.output
        # Status message prose should appear
        assert "in progress" in result.output
        # "As of" date should appear
        assert "February 07, 2026" in result.output

    def test_status_no_expiration_no_crash(self, saved_config):
        """Status without expiration_date doesn't crash (prose-only response)."""
        minimal_status = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            status=StatusType.PENDING,
        )
        mock_provider = _make_mock_provider(minimal_status)
        mock_bm = _make_mock_browser_manager()
        mock_provider_cls = MagicMock(return_value=mock_provider)

        with (
            patch("faaadmv.cli.commands.status.ConfigManager", return_value=saved_config),
            patch("faaadmv.cli.commands.status.BrowserManager", return_value=mock_bm),
            patch("faaadmv.cli.commands.status.get_provider", return_value=mock_provider_cls),
        ):
            result = runner.invoke(
                app,
                ["status"],
                input="testpass\n",
            )

        print("MINIMAL STATUS OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Minimal status failed: {result.output}"
        assert "Pending" in result.output
        assert "8ABC123" in result.output
        # Should NOT show "Expires" or "Days left" since no expiration_date
        assert "Expires" not in result.output
        assert "Days left" not in result.output
