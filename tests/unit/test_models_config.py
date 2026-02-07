"""Tests for UserConfig model."""

import pytest
from pydantic import ValidationError

from faaadmv.models.config import UserConfig
from faaadmv.models.owner import Address, OwnerInfo
from faaadmv.models.payment import PaymentInfo
from faaadmv.models.vehicle import VehicleInfo


@pytest.fixture
def sample_vehicle():
    return VehicleInfo(plate="8ABC123", vin_last5="12345")


@pytest.fixture
def sample_address():
    return Address(street="123 Main St", city="Los Angeles", state="CA", zip_code="90001")


@pytest.fixture
def sample_owner(sample_address):
    return OwnerInfo(
        full_name="Jane Doe",
        phone="5551234567",
        email="jane@example.com",
        address=sample_address,
    )


@pytest.fixture
def sample_payment():
    return PaymentInfo(
        card_number="4242424242424242",
        expiry_month=12,
        expiry_year=2027,
        cvv="123",
        billing_zip="90001",
    )


class TestUserConfig:
    def test_basic_creation(self, sample_vehicle, sample_owner):
        config = UserConfig(vehicle=sample_vehicle, owner=sample_owner)
        assert config.vehicle.plate == "8ABC123"
        assert config.owner.full_name == "Jane Doe"
        assert config.version == 1
        assert config.state == "CA"

    def test_payment_excluded_by_default(self, sample_vehicle, sample_owner):
        config = UserConfig(vehicle=sample_vehicle, owner=sample_owner)
        assert config.payment is None
        assert config.has_payment is False

    def test_with_payment(self, sample_vehicle, sample_owner, sample_payment):
        config = UserConfig(vehicle=sample_vehicle, owner=sample_owner)
        config_with_pay = config.with_payment(sample_payment)
        assert config_with_pay.has_payment is True
        assert config_with_pay.payment.masked_number == "****4242"

    def test_payment_excluded_from_serialization(self, sample_vehicle, sample_owner, sample_payment):
        config = UserConfig(vehicle=sample_vehicle, owner=sample_owner)
        config_with_pay = config.with_payment(sample_payment)
        dumped = config_with_pay.model_dump(mode="json", exclude_none=True)
        assert "payment" not in dumped

    def test_summary(self, sample_vehicle, sample_owner):
        config = UserConfig(vehicle=sample_vehicle, owner=sample_owner)
        summary = config.summary
        assert summary["plate"] == "8ABC123"
        assert summary["owner"] == "Jane Doe"
        assert summary["state"] == "CA"
        assert "***" in summary["vin"]

    def test_timestamps_set(self, sample_vehicle, sample_owner):
        config = UserConfig(vehicle=sample_vehicle, owner=sample_owner)
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_custom_state(self, sample_vehicle, sample_owner):
        config = UserConfig(vehicle=sample_vehicle, owner=sample_owner, state="TX")
        assert config.state == "TX"

    def test_invalid_state_format(self, sample_vehicle, sample_owner):
        with pytest.raises(ValidationError):
            UserConfig(vehicle=sample_vehicle, owner=sample_owner, state="California")
