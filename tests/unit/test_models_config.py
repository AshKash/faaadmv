"""Tests for UserConfig model."""

import pytest
from pydantic import ValidationError

from faaadmv.models.config import UserConfig
from faaadmv.models.owner import Address, OwnerInfo
from faaadmv.models.payment import PaymentInfo
from faaadmv.models.vehicle import VehicleEntry, VehicleInfo


@pytest.fixture
def sample_vehicle():
    return VehicleInfo(plate="8ABC123", vin_last5="12345")


@pytest.fixture
def sample_entry(sample_vehicle):
    return VehicleEntry(vehicle=sample_vehicle, is_default=True)


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
    def test_basic_creation(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        assert config.vehicle.plate == "8ABC123"
        assert config.owner.full_name == "Jane Doe"
        assert config.version == 2
        assert config.state == "CA"

    def test_payment_excluded_by_default(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        assert config.payment is None
        assert config.has_payment is False

    def test_with_payment(self, sample_entry, sample_owner, sample_payment):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        config_with_pay = config.with_payment(sample_payment)
        assert config_with_pay.has_payment is True
        assert config_with_pay.payment.masked_number == "****4242"

    def test_payment_excluded_from_serialization(self, sample_entry, sample_owner, sample_payment):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        config_with_pay = config.with_payment(sample_payment)
        dumped = config_with_pay.model_dump(mode="json", exclude_none=True)
        assert "payment" not in dumped

    def test_summary(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        summary = config.summary
        assert summary["plate"] == "8ABC123"
        assert summary["owner"] == "Jane Doe"
        assert summary["state"] == "CA"
        assert "***" in summary["vin"]

    def test_timestamps_set(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        assert config.created_at is not None
        assert config.updated_at is not None

    def test_custom_state(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner, state="TX")
        assert config.state == "TX"

    def test_invalid_state_format(self, sample_entry, sample_owner):
        with pytest.raises(ValidationError):
            UserConfig(vehicles=[sample_entry], owner=sample_owner, state="California")

    def test_no_vehicles_raises(self, sample_owner):
        with pytest.raises(ValidationError):
            UserConfig(vehicles=[], owner=sample_owner)

    def test_vehicle_backward_compat(self, sample_entry, sample_owner):
        """config.vehicle returns default vehicle's VehicleInfo."""
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        assert config.vehicle is config.default_vehicle.vehicle

    def test_default_vehicle(self, sample_owner):
        v1 = VehicleEntry(vehicle=VehicleInfo(plate="AAA111", vin_last5="11111"), is_default=False)
        v2 = VehicleEntry(vehicle=VehicleInfo(plate="BBB222", vin_last5="22222"), is_default=True)
        config = UserConfig(vehicles=[v1, v2], owner=sample_owner)
        assert config.default_vehicle.plate == "BBB222"

    def test_default_vehicle_fallback(self, sample_owner):
        """First vehicle used when none marked default."""
        v1 = VehicleEntry(vehicle=VehicleInfo(plate="AAA111", vin_last5="11111"))
        v2 = VehicleEntry(vehicle=VehicleInfo(plate="BBB222", vin_last5="22222"))
        config = UserConfig(vehicles=[v1, v2], owner=sample_owner)
        assert config.default_vehicle.plate == "AAA111"

    def test_get_vehicle(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        found = config.get_vehicle("8ABC123")
        assert found is not None
        assert found.plate == "8ABC123"

    def test_get_vehicle_not_found(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        assert config.get_vehicle("ZZZZZ") is None

    def test_add_vehicle(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        new_v = VehicleInfo(plate="NEW1234", vin_last5="99999")
        updated = config.add_vehicle(new_v, nickname="Second car")
        assert len(updated.vehicles) == 2
        assert updated.get_vehicle("NEW1234").nickname == "Second car"

    def test_add_vehicle_as_default(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        new_v = VehicleInfo(plate="NEW1234", vin_last5="99999")
        updated = config.add_vehicle(new_v, is_default=True)
        assert updated.default_vehicle.plate == "NEW1234"
        # Old default cleared
        assert not updated.get_vehicle("8ABC123").is_default

    def test_remove_vehicle(self, sample_owner):
        v1 = VehicleEntry(vehicle=VehicleInfo(plate="AAA111", vin_last5="11111"), is_default=True)
        v2 = VehicleEntry(vehicle=VehicleInfo(plate="BBB222", vin_last5="22222"))
        config = UserConfig(vehicles=[v1, v2], owner=sample_owner)
        updated = config.remove_vehicle("BBB222")
        assert len(updated.vehicles) == 1
        assert updated.vehicles[0].plate == "AAA111"

    def test_remove_last_vehicle_raises(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        with pytest.raises(ValueError, match="Cannot remove the last vehicle"):
            config.remove_vehicle("8ABC123")

    def test_remove_default_promotes_next(self, sample_owner):
        v1 = VehicleEntry(vehicle=VehicleInfo(plate="AAA111", vin_last5="11111"), is_default=True)
        v2 = VehicleEntry(vehicle=VehicleInfo(plate="BBB222", vin_last5="22222"))
        config = UserConfig(vehicles=[v1, v2], owner=sample_owner)
        updated = config.remove_vehicle("AAA111")
        assert updated.default_vehicle.plate == "BBB222"
        assert updated.default_vehicle.is_default

    def test_set_default(self, sample_owner):
        v1 = VehicleEntry(vehicle=VehicleInfo(plate="AAA111", vin_last5="11111"), is_default=True)
        v2 = VehicleEntry(vehicle=VehicleInfo(plate="BBB222", vin_last5="22222"))
        config = UserConfig(vehicles=[v1, v2], owner=sample_owner)
        updated = config.set_default("BBB222")
        assert updated.default_vehicle.plate == "BBB222"
        assert not updated.get_vehicle("AAA111").is_default

    def test_set_default_not_found(self, sample_entry, sample_owner):
        config = UserConfig(vehicles=[sample_entry], owner=sample_owner)
        with pytest.raises(ValueError, match="not found"):
            config.set_default("ZZZZZ")
