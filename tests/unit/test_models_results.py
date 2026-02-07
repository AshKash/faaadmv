"""Tests for result models."""

import pytest
from datetime import date
from decimal import Decimal

from faaadmv.models.results import (
    EligibilityResult,
    FeeBreakdown,
    FeeItem,
    InsuranceStatus,
    RegistrationStatus,
    RenewalResult,
    SmogStatus,
    StatusType,
)


class TestStatusType:
    def test_values(self):
        assert StatusType.CURRENT == "current"
        assert StatusType.EXPIRED == "expired"
        assert StatusType.PENDING == "pending"
        assert StatusType.EXPIRING_SOON == "expiring_soon"
        assert StatusType.HOLD == "hold"


class TestRegistrationStatus:
    def test_current_is_renewable(self):
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            expiration_date=date(2026, 6, 20),
            status=StatusType.CURRENT,
            days_until_expiry=133,
        )
        assert s.is_renewable is True

    def test_expiring_soon_is_renewable(self):
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            expiration_date=date(2026, 4, 1),
            status=StatusType.EXPIRING_SOON,
            days_until_expiry=53,
        )
        assert s.is_renewable is True

    def test_expired_not_renewable(self):
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            expiration_date=date(2025, 1, 1),
            status=StatusType.EXPIRED,
            days_until_expiry=-400,
        )
        assert s.is_renewable is False

    def test_hold_not_renewable(self):
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            expiration_date=date(2026, 6, 20),
            status=StatusType.HOLD,
            days_until_expiry=133,
            hold_reason="Unpaid parking tickets",
        )
        assert s.is_renewable is False

    def test_status_display(self):
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            expiration_date=date(2026, 6, 20),
            status=StatusType.CURRENT,
            days_until_expiry=133,
        )
        assert s.status_display == "Current"

    def test_status_emoji(self):
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            expiration_date=date(2026, 6, 20),
            status=StatusType.EXPIRED,
            days_until_expiry=-10,
        )
        assert s.status_emoji == "\u2717"

    def test_status_emoji_current(self):
        s = RegistrationStatus(
            plate="8ABC123", vin_last5="12345", status=StatusType.CURRENT,
        )
        assert s.status_emoji == "\u2713"

    def test_status_message_field(self):
        msg = "An application for Vehicle Registration 8ABC123 is in progress."
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            status=StatusType.PENDING,
            status_message=msg,
        )
        assert s.status_message == msg

    def test_last_updated_field(self):
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            status=StatusType.CURRENT,
            last_updated=date(2026, 2, 7),
        )
        assert s.last_updated == date(2026, 2, 7)

    def test_optional_fields_default_none(self):
        """Status from prose-only DMV page: no expiration_date or days."""
        s = RegistrationStatus(
            plate="8ABC123",
            vin_last5="12345",
            status=StatusType.PENDING,
        )
        assert s.expiration_date is None
        assert s.days_until_expiry is None
        assert s.vehicle_description is None
        assert s.status_message is None
        assert s.last_updated is None
        assert s.hold_reason is None

    def test_status_display_all_types(self):
        for st, expected in [
            (StatusType.CURRENT, "Current"),
            (StatusType.EXPIRING_SOON, "Expiring Soon"),
            (StatusType.PENDING, "Pending"),
            (StatusType.EXPIRED, "Expired"),
            (StatusType.HOLD, "Hold"),
        ]:
            s = RegistrationStatus(plate="X", vin_last5="12345", status=st)
            assert s.status_display == expected


class TestFeeBreakdown:
    def test_total_calculation(self):
        fb = FeeBreakdown(items=[
            FeeItem(description="Registration", amount=Decimal("168.00")),
            FeeItem(description="CHP Fee", amount=Decimal("32.00")),
            FeeItem(description="County Fee", amount=Decimal("48.00")),
        ])
        assert fb.total == Decimal("248.00")
        assert fb.total_display == "$248.00"

    def test_empty_fees(self):
        fb = FeeBreakdown(items=[])
        assert fb.total == Decimal("0")

    def test_fee_item_display(self):
        item = FeeItem(description="Registration", amount=Decimal("168.00"))
        assert item.amount_display == "$168.00"


class TestRenewalResult:
    def test_success_result(self):
        r = RenewalResult(
            success=True,
            confirmation_number="CONF-12345",
            new_expiration_date=date(2027, 2, 1),
            amount_paid=Decimal("248.00"),
        )
        assert r.success is True
        assert r.amount_display == "$248.00"

    def test_failure_result(self):
        r = RenewalResult(
            success=False,
            error_message="Payment declined",
        )
        assert r.success is False
        assert r.amount_display == ""


class TestEligibilityResult:
    def test_eligible(self):
        e = EligibilityResult(
            eligible=True,
            smog=SmogStatus(passed=True, check_date=date(2026, 1, 15)),
            insurance=InsuranceStatus(verified=True, provider="State Farm"),
        )
        assert e.eligible is True
        assert e.smog.passed is True
        assert e.insurance.verified is True

    def test_not_eligible(self):
        e = EligibilityResult(
            eligible=False,
            smog=SmogStatus(passed=False),
            insurance=InsuranceStatus(verified=True),
            error_message="Smog check failed",
        )
        assert e.eligible is False
