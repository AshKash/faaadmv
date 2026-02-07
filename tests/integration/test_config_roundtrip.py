"""Integration tests for ConfigManager + Crypto roundtrip."""

import pytest

from faaadmv.core.config import ConfigManager
from faaadmv.models.config import UserConfig
from faaadmv.models.owner import Address, OwnerInfo
from faaadmv.models.vehicle import VehicleInfo


@pytest.fixture
def full_config():
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
        state="CA",
    )


class TestConfigRoundtrip:
    def test_save_load_full_config(self, temp_config_dir, full_config):
        """Full save-load cycle preserves all data."""
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(full_config, passphrase="my-secret")

        loaded = manager.load(passphrase="my-secret")

        # Vehicle
        assert loaded.vehicle.plate == "8ABC123"
        assert loaded.vehicle.vin_last5 == "12345"

        # Owner
        assert loaded.owner.full_name == "Jane Doe"
        assert loaded.owner.phone == "5551234567"
        assert loaded.owner.email == "jane@example.com"

        # Address
        assert loaded.owner.address.street == "123 Main St"
        assert loaded.owner.address.city == "Los Angeles"
        assert loaded.owner.address.state == "CA"
        assert loaded.owner.address.zip_code == "90001"

        # Metadata
        assert loaded.state == "CA"
        assert loaded.version == 1

    def test_payment_not_in_encrypted_file(self, temp_config_dir, full_config):
        """Payment data should NOT be in the encrypted config file."""
        from faaadmv.models.payment import PaymentInfo

        config_with_pay = full_config.with_payment(
            PaymentInfo(
                card_number="4242424242424242",
                expiry_month=12,
                expiry_year=2027,
                cvv="123",
                billing_zip="90001",
            )
        )

        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(config_with_pay, passphrase="test")

        # Load back — payment should be None (excluded from serialization)
        loaded = manager.load(passphrase="test")
        assert loaded.payment is None

    def test_save_delete_save_cycle(self, temp_config_dir, full_config):
        """Config can be deleted and re-saved."""
        manager = ConfigManager(config_dir=temp_config_dir)

        manager.save(full_config, passphrase="pass1")
        assert manager.exists is True

        manager.delete()
        assert manager.exists is False

        manager.save(full_config, passphrase="pass2")
        loaded = manager.load(passphrase="pass2")
        assert loaded.vehicle.plate == "8ABC123"

    def test_config_file_is_not_readable_toml(self, temp_config_dir, full_config):
        """Raw file should not be valid TOML (it's encrypted)."""
        import tomli

        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(full_config, passphrase="test")

        raw = manager.config_path.read_bytes()
        with pytest.raises(Exception):
            tomli.loads(raw.decode("utf-8", errors="replace"))
