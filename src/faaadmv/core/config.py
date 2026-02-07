"""Configuration management."""

from pathlib import Path
from typing import Optional

import platformdirs
import tomli
import tomli_w

from faaadmv.core.crypto import ConfigCrypto
from faaadmv.exceptions import ConfigNotFoundError, ConfigValidationError
from faaadmv.models import UserConfig

# Current config schema version
CURRENT_VERSION = 2


class ConfigManager:
    """Manages encrypted configuration storage."""

    CONFIG_FILENAME = "config.enc"

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        """Initialize config manager.

        Args:
            config_dir: Override config directory (for testing)
        """
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            self._config_dir = Path(
                platformdirs.user_config_dir("faaadmv", ensure_exists=True)
            )

    @property
    def config_path(self) -> Path:
        """Path to encrypted config file."""
        return self._config_dir / self.CONFIG_FILENAME

    @property
    def exists(self) -> bool:
        """Check if config file exists."""
        return self.config_path.exists()

    def save(self, config: UserConfig, passphrase: str) -> None:
        """Save configuration to encrypted file.

        Args:
            config: User configuration to save
            passphrase: Passphrase for encryption
        """
        # Ensure directory exists
        self._config_dir.mkdir(parents=True, exist_ok=True)

        # Serialize to TOML
        config_dict = config.model_dump(mode="json", exclude_none=True)
        toml_str = tomli_w.dumps(config_dict)

        # Encrypt and write
        crypto = ConfigCrypto(passphrase)
        encrypted = crypto.encrypt(toml_str)
        self.config_path.write_bytes(encrypted)

    def load(self, passphrase: str) -> UserConfig:
        """Load configuration from encrypted file.

        Args:
            passphrase: Passphrase for decryption

        Returns:
            Loaded and validated UserConfig

        Raises:
            ConfigNotFoundError: If config file doesn't exist
            ConfigDecryptionError: If passphrase is wrong
            ConfigValidationError: If config is invalid
        """
        if not self.exists:
            raise ConfigNotFoundError()

        # Read and decrypt
        encrypted = self.config_path.read_bytes()
        crypto = ConfigCrypto(passphrase)
        toml_str = crypto.decrypt(encrypted)

        # Parse TOML
        config_dict = tomli.loads(toml_str)

        # Apply migrations if needed
        config_dict = self._migrate(config_dict)

        # Validate and return
        try:
            return UserConfig.model_validate(config_dict)
        except Exception as e:
            raise ConfigValidationError("config", str(e))

    def delete(self) -> bool:
        """Delete configuration file.

        Returns:
            True if file was deleted, False if it didn't exist
        """
        if self.exists:
            self.config_path.unlink()
            return True
        return False

    def _migrate(self, config_dict: dict) -> dict:
        """Apply schema migrations.

        Args:
            config_dict: Raw config dictionary

        Returns:
            Migrated config dictionary
        """
        version = config_dict.get("version", 1)

        # Apply migrations sequentially
        migrations = {
            # v1 → v2: single vehicle → vehicle list
            2: self._migrate_v1_to_v2,
        }

        for target_version in range(version + 1, CURRENT_VERSION + 1):
            if target_version in migrations:
                config_dict = migrations[target_version](config_dict)
                config_dict["version"] = target_version

        return config_dict

    @staticmethod
    def _migrate_v1_to_v2(config_dict: dict) -> dict:
        """Migrate v1 (single vehicle) to v2 (vehicle list).

        v1 schema: {vehicle: {plate, vin_last5}, owner: {...}, ...}
        v2 schema: {vehicles: [{vehicle: {plate, vin_last5}, is_default: true}], owner: {...}, ...}
        """
        if "vehicle" in config_dict and "vehicles" not in config_dict:
            vehicle_data = config_dict.pop("vehicle")
            config_dict["vehicles"] = [
                {
                    "vehicle": vehicle_data,
                    "is_default": True,
                }
            ]
        return config_dict
