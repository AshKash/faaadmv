"""Tests for PaymentInfo model."""

import pytest
from pydantic import ValidationError

from faaadmv.models.payment import PaymentInfo


# Known Luhn-valid test card numbers
VISA_CARD = "4242424242424242"
MASTERCARD = "5555555555554444"
AMEX_CARD = "378282246310005"


class TestPaymentInfoValid:
    def test_visa_card(self):
        p = PaymentInfo(
            card_number=VISA_CARD,
            expiry_month=12,
            expiry_year=2027,
            cvv="123",
            billing_zip="90001",
        )
        assert p.masked_number == "****4242"
        assert p.card_type == "Visa"

    def test_mastercard(self):
        p = PaymentInfo(
            card_number=MASTERCARD,
            expiry_month=6,
            expiry_year=2028,
            cvv="456",
            billing_zip="10001",
        )
        assert p.masked_number == "****4444"
        assert p.card_type == "Mastercard"

    def test_amex_card(self):
        p = PaymentInfo(
            card_number=AMEX_CARD,
            expiry_month=3,
            expiry_year=2029,
            cvv="1234",
            billing_zip="90001",
        )
        assert p.masked_number == "****0005"
        assert p.card_type == "Amex"

    def test_expiry_display(self):
        p = PaymentInfo(
            card_number=VISA_CARD,
            expiry_month=1,
            expiry_year=2027,
            cvv="123",
            billing_zip="90001",
        )
        assert p.expiry_display == "01/27"

    def test_not_expired(self):
        p = PaymentInfo(
            card_number=VISA_CARD,
            expiry_month=12,
            expiry_year=2030,
            cvv="123",
            billing_zip="90001",
        )
        assert p.is_expired is False

    def test_expired_card(self):
        p = PaymentInfo(
            card_number=VISA_CARD,
            expiry_month=1,
            expiry_year=2024,
            cvv="123",
            billing_zip="90001",
        )
        assert p.is_expired is True

    def test_cvv_three_digits(self):
        p = PaymentInfo(
            card_number=VISA_CARD,
            expiry_month=12,
            expiry_year=2027,
            cvv="123",
            billing_zip="90001",
        )
        assert p.cvv.get_secret_value() == "123"

    def test_cvv_four_digits(self):
        p = PaymentInfo(
            card_number=VISA_CARD,
            expiry_month=12,
            expiry_year=2027,
            cvv="1234",
            billing_zip="90001",
        )
        assert p.cvv.get_secret_value() == "1234"


class TestPaymentInfoInvalid:
    def test_luhn_invalid(self):
        with pytest.raises(ValidationError) as exc_info:
            PaymentInfo(
                card_number="1234567890123456",
                expiry_month=12,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )
        assert "Luhn" in str(exc_info.value)

    def test_card_too_short(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number="424242424242",
                expiry_month=12,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )

    def test_card_non_digits(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number="4242-4242-4242-abcd",
                expiry_month=12,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )

    def test_cvv_too_short(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number=VISA_CARD,
                expiry_month=12,
                expiry_year=2027,
                cvv="12",
                billing_zip="90001",
            )

    def test_cvv_too_long(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number=VISA_CARD,
                expiry_month=12,
                expiry_year=2027,
                cvv="12345",
                billing_zip="90001",
            )

    def test_cvv_non_digits(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number=VISA_CARD,
                expiry_month=12,
                expiry_year=2027,
                cvv="abc",
                billing_zip="90001",
            )

    def test_expiry_month_zero(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number=VISA_CARD,
                expiry_month=0,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )

    def test_expiry_month_13(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number=VISA_CARD,
                expiry_month=13,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )

    def test_expiry_year_too_old(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number=VISA_CARD,
                expiry_month=12,
                expiry_year=2023,
                cvv="123",
                billing_zip="90001",
            )

    def test_invalid_billing_zip(self):
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number=VISA_CARD,
                expiry_month=12,
                expiry_year=2027,
                cvv="123",
                billing_zip="9000",
            )


class TestLuhnAlgorithm:
    """Verify the Luhn algorithm itself."""

    def test_known_valid_numbers(self):
        assert PaymentInfo._luhn_check("4242424242424242") is True
        assert PaymentInfo._luhn_check("5555555555554444") is True
        assert PaymentInfo._luhn_check("378282246310005") is True

    def test_known_invalid_numbers(self):
        assert PaymentInfo._luhn_check("1234567890123456") is False

    def test_all_zeros_rejected_by_validator(self):
        # BUG-003 FIXED: all-zeros now rejected before Luhn check
        with pytest.raises(ValidationError):
            PaymentInfo(
                card_number="0000000000000000",
                expiry_month=12,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )
