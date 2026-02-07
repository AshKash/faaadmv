"""Tests for CA DMV provider parsing logic.

Tests _determine_status_from_text, _parse_date, _parse_amount — the core
logic that interprets DMV website responses into structured data.
These are P0 tests: if parsing breaks, status/renew won't work.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from faaadmv.models.results import StatusType
from faaadmv.providers.ca_dmv import CADMVProvider


@pytest.fixture
def provider():
    """Create a CADMVProvider without a real browser context."""
    p = CADMVProvider.__new__(CADMVProvider)
    p.context = MagicMock()
    p.page = None
    return p


class TestDetermineStatusFromText:
    """Test _determine_status_from_text — maps DMV prose to StatusType."""

    def test_mailed_status(self, provider):
        """'has been mailed' → CURRENT."""
        text = "Your registration card has been mailed to you as of February 05, 2026."
        assert provider._determine_status_from_text(text) == StatusType.CURRENT

    def test_was_mailed_status(self, provider):
        """'was mailed' → CURRENT."""
        text = "Your registration was mailed on January 20, 2026."
        assert provider._determine_status_from_text(text) == StatusType.CURRENT

    def test_in_progress_status(self, provider):
        """'in progress' → PENDING."""
        text = (
            "An application for Vehicle Registration 8ABC123 is in progress "
            "as of February 07, 2026. Your registration has not yet been mailed. "
            "No further action is required."
        )
        assert provider._determine_status_from_text(text) == StatusType.PENDING

    def test_not_yet_mailed_status(self, provider):
        """'not yet been mailed' → PENDING."""
        text = "Your registration has not yet been mailed. No further action is required."
        assert provider._determine_status_from_text(text) == StatusType.PENDING

    def test_not_yet_received_status(self, provider):
        """'not yet received' → PENDING."""
        text = "Your renewal application has not yet received by DMV."
        assert provider._determine_status_from_text(text) == StatusType.PENDING

    def test_items_due_with_action_required(self, provider):
        """'action is required' (without 'no further') → HOLD."""
        text = "Items due on your registration. Action is required before processing."
        assert provider._determine_status_from_text(text) == StatusType.HOLD

    def test_no_further_action_is_pending(self, provider):
        """'no further action is required' → PENDING (not HOLD)."""
        text = "Processing your registration. No further action is required at this time."
        assert provider._determine_status_from_text(text) == StatusType.PENDING

    def test_expired_status(self, provider):
        """'expired' → EXPIRED."""
        text = "Your vehicle registration has expired as of December 31, 2025."
        assert provider._determine_status_from_text(text) == StatusType.EXPIRED

    def test_unknown_text_defaults_pending(self, provider):
        """Unknown/unrecognized prose → defaults to PENDING."""
        text = "Something completely unexpected from the DMV website."
        assert provider._determine_status_from_text(text) == StatusType.PENDING

    def test_case_insensitive(self, provider):
        """Matching is case-insensitive."""
        text = "Your registration card HAS BEEN MAILED to you."
        assert provider._determine_status_from_text(text) == StatusType.CURRENT

    def test_items_due_keyword(self, provider):
        """'items due' → HOLD."""
        text = "There are items due for this vehicle. Please visit your local DMV."
        assert provider._determine_status_from_text(text) == StatusType.HOLD


class TestParseDate:
    """Test _parse_date — extracts dates from various DMV formats."""

    def test_month_day_year(self, provider):
        """Standard 'Month DD, YYYY' format."""
        assert provider._parse_date("February 07, 2026") == date(2026, 2, 7)

    def test_slash_format(self, provider):
        """MM/DD/YYYY format."""
        assert provider._parse_date("02/07/2026") == date(2026, 2, 7)

    def test_iso_format(self, provider):
        """YYYY-MM-DD format."""
        assert provider._parse_date("2026-02-07") == date(2026, 2, 7)

    def test_date_within_longer_text(self, provider):
        """Date embedded in a sentence."""
        assert provider._parse_date("as of February 07, 2026 your") == date(2026, 2, 7)

    def test_slash_date_within_text(self, provider):
        """Slash date embedded in text."""
        assert provider._parse_date("updated on 02/07/2026 by") == date(2026, 2, 7)

    def test_invalid_date_returns_none(self, provider):
        """Unrecognizable text → None."""
        assert provider._parse_date("no date here") is None

    def test_empty_string(self, provider):
        assert provider._parse_date("") is None

    def test_whitespace_around_date(self, provider):
        assert provider._parse_date("  January 15, 2026  ") == date(2026, 1, 15)


class TestParseAmount:
    """Test _parse_amount — extracts dollar amounts from text."""

    def test_simple_dollar(self, provider):
        assert provider._parse_amount("$168.00") == Decimal("168.00")

    def test_no_dollar_sign(self, provider):
        assert provider._parse_amount("168.00") == Decimal("168.00")

    def test_with_comma(self, provider):
        assert provider._parse_amount("$1,248.00") == Decimal("1248.00")

    def test_in_text(self, provider):
        assert provider._parse_amount("Total: $248.00 due") == Decimal("248.00")

    def test_no_amount(self, provider):
        assert provider._parse_amount("no amount") == Decimal("0")

    def test_integer_amount(self, provider):
        assert provider._parse_amount("$32") == Decimal("32")


class TestDetermineStatus:
    """Test _determine_status — the text + days_left version."""

    def test_expired_from_text(self, provider):
        assert provider._determine_status("EXPIRED", 0) == StatusType.EXPIRED

    def test_pending_from_text(self, provider):
        assert provider._determine_status("Pending review", 100) == StatusType.PENDING

    def test_hold_from_text(self, provider):
        assert provider._determine_status("On hold", 100) == StatusType.HOLD

    def test_expiring_soon_from_days(self, provider):
        """Within 90 days and no keyword → EXPIRING_SOON."""
        assert provider._determine_status("Registration valid", 45) == StatusType.EXPIRING_SOON

    def test_current_from_days(self, provider):
        """More than 90 days → CURRENT."""
        assert provider._determine_status("Registration valid", 200) == StatusType.CURRENT

    def test_boundary_90_days(self, provider):
        """Exactly 90 days → EXPIRING_SOON."""
        assert provider._determine_status("Registration valid", 90) == StatusType.EXPIRING_SOON


class TestGetSelectors:
    """Verify selector dictionary has required keys for status + renew flows."""

    def test_status_selectors_present(self, provider):
        selectors = provider.get_selectors()
        required = [
            "status_plate_input", "status_continue",
            "status_vin_input", "status_vin_not_found",
            "status_results_fieldset", "status_results_legend",
        ]
        for key in required:
            assert key in selectors, f"Missing selector: {key}"

    def test_renew_selectors_present(self, provider):
        selectors = provider.get_selectors()
        required = [
            "renew_plate_input", "renew_vin_input", "renew_continue",
        ]
        for key in required:
            assert key in selectors, f"Missing selector: {key}"

    def test_error_selectors_present(self, provider):
        selectors = provider.get_selectors()
        assert "error_message" in selectors
        assert "confirmation_number" in selectors
