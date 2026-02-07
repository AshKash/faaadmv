"""Integration tests for PaymentKeychain with mock keyring."""

import pytest

from faaadmv.core.keychain import PaymentKeychain
from faaadmv.models.payment import PaymentInfo


VISA_CARD = "4242424242424242"


@pytest.fixture
def sample_payment():
    return PaymentInfo(
        card_number=VISA_CARD,
        expiry_month=12,
        expiry_year=2027,
        cvv="123",
        billing_zip="90001",
    )


class TestPaymentKeychain:
    def test_store_and_retrieve(self, mock_keyring, sample_payment):
        PaymentKeychain.store(sample_payment)
        retrieved = PaymentKeychain.retrieve()

        assert retrieved is not None
        assert retrieved.card_number.get_secret_value() == VISA_CARD
        assert retrieved.expiry_month == 12
        assert retrieved.expiry_year == 2027
        assert retrieved.cvv.get_secret_value() == "123"
        assert retrieved.billing_zip == "90001"

    def test_retrieve_when_empty(self, mock_keyring):
        retrieved = PaymentKeychain.retrieve()
        assert retrieved is None

    def test_exists_when_stored(self, mock_keyring, sample_payment):
        assert PaymentKeychain.exists() is False
        PaymentKeychain.store(sample_payment)
        assert PaymentKeychain.exists() is True

    def test_delete(self, mock_keyring, sample_payment):
        PaymentKeychain.store(sample_payment)
        assert PaymentKeychain.exists() is True

        PaymentKeychain.delete()
        assert PaymentKeychain.exists() is False

    def test_delete_when_empty(self, mock_keyring):
        # Should not raise
        PaymentKeychain.delete()

    def test_store_overwrites(self, mock_keyring, sample_payment):
        PaymentKeychain.store(sample_payment)

        new_payment = PaymentInfo(
            card_number="5555555555554444",
            expiry_month=6,
            expiry_year=2028,
            cvv="456",
            billing_zip="10001",
        )
        PaymentKeychain.store(new_payment)

        retrieved = PaymentKeychain.retrieve()
        assert retrieved is not None
        assert retrieved.card_number.get_secret_value() == "5555555555554444"
        assert retrieved.expiry_month == 6

    def test_roundtrip_preserves_masked_number(self, mock_keyring, sample_payment):
        PaymentKeychain.store(sample_payment)
        retrieved = PaymentKeychain.retrieve()
        assert retrieved.masked_number == "****4242"

    def test_roundtrip_preserves_card_type(self, mock_keyring, sample_payment):
        PaymentKeychain.store(sample_payment)
        retrieved = PaymentKeychain.retrieve()
        assert retrieved.card_type == "Visa"
