"""Tests for ConfigManager."""

import pytest

from faaadmv.core.config import ConfigManager
from faaadmv.exceptions import ConfigDecryptionError, ConfigNotFoundError
from faaadmv.models.config import UserConfig
from faaadmv.models.owner import Address, OwnerInfo
from faaadmv.models.vehicle import VehicleInfo


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
        assert loaded.vehicle.plate == "8ABC123"
        assert loaded.owner.full_name == "Jane Doe"

    def test_config_file_created(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="test123")
        assert manager.config_path.exists()

    def test_config_file_encrypted(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="test123")
        contents = manager.config_path.read_bytes()
        assert b"Jane Doe" not in contents
        assert b"8ABC123" not in contents

    def test_exists_property(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        assert manager.exists is False
        manager.save(sample_config, passphrase="test123")
        assert manager.exists is True

    def test_wrong_passphrase(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="correct")
        with pytest.raises(ConfigDecryptionError):
            manager.load(passphrase="wrong")

    def test_config_not_found(self, temp_config_dir):
        manager = ConfigManager(config_dir=temp_config_dir)
        with pytest.raises(ConfigNotFoundError):
            manager.load(passphrase="any")

    def test_delete_existing(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="test123")
        assert manager.delete() is True
        assert manager.exists is False

    def test_delete_nonexistent(self, temp_config_dir):
        manager = ConfigManager(config_dir=temp_config_dir)
        assert manager.delete() is False

    def test_overwrite_config(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="pass1")

        # Update and re-save
        new_config = UserConfig(
            vehicle=VehicleInfo(plate="NEWPLATE", vin_last5="99999"),
            owner=sample_config.owner,
        )
        manager.save(new_config, passphrase="pass2")

        loaded = manager.load(passphrase="pass2")
        assert loaded.vehicle.plate == "NEWPLATE"

    def test_config_preserves_all_fields(self, temp_config_dir, sample_config):
        manager = ConfigManager(config_dir=temp_config_dir)
        manager.save(sample_config, passphrase="test")
        loaded = manager.load(passphrase="test")

        assert loaded.vehicle.plate == sample_config.vehicle.plate
        assert loaded.vehicle.vin_last5 == sample_config.vehicle.vin_last5
        assert loaded.owner.full_name == sample_config.owner.full_name
        assert loaded.owner.phone == sample_config.owner.phone
        assert loaded.owner.email == sample_config.owner.email
        assert loaded.owner.address.street == sample_config.owner.address.street
        assert loaded.owner.address.city == sample_config.owner.address.city
        assert loaded.owner.address.state == sample_config.owner.address.state
        assert loaded.owner.address.zip_code == sample_config.owner.address.zip_code
        assert loaded.state == sample_config.state

    def test_creates_config_dir(self, tmp_path, sample_config):
        new_dir = tmp_path / "nonexistent" / "config"
        manager = ConfigManager(config_dir=new_dir)
        manager.save(sample_config, passphrase="test")
        assert new_dir.exists()
        assert manager.config_path.exists()
