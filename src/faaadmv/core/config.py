"""Configuration management."""

import logging
import os
from pathlib import Path
from typing import Optional

import platformdirs
import tomli
import tomli_w

from faaadmv.exceptions import ConfigNotFoundError, ConfigValidationError
from faaadmv.models import UserConfig

logger = logging.getLogger(__name__)

# Current config schema version
CURRENT_VERSION = 2


class ConfigManager:
    """Manages configuration storage as plain TOML."""

    CONFIG_FILENAME = "config.toml"

    def __init__(self, config_dir: Optional[Path] = None) -> None:
        if config_dir:
            self._config_dir = Path(config_dir)
        else:
            env_dir = os.environ.get("FAAADM_CONFIG_DIR")
            if env_dir:
                self._config_dir = Path(env_dir)
                return
            self._config_dir = Path(
                platformdirs.user_config_dir("faaadmv", ensure_exists=True)
            )

    @property
    def config_path(self) -> Path:
        return self._config_dir / self.CONFIG_FILENAME

    @property
    def exists(self) -> bool:
        return self.config_path.exists()

    def save(self, config: UserConfig) -> None:
        """Save configuration to TOML file."""
        self._config_dir.mkdir(parents=True, exist_ok=True)

        config_dict = config.model_dump(mode="json", exclude_none=True)
        toml_str = tomli_w.dumps(config_dict)
        self.config_path.write_text(toml_str, encoding="utf-8")
        logger.debug("Config saved to %s", self.config_path)

    def load(self) -> UserConfig:
        """Load configuration from TOML file.

        Raises:
            ConfigNotFoundError: If config file doesn't exist
            ConfigValidationError: If config is invalid
        """
        if not self.exists:
            raise ConfigNotFoundError()

        logger.debug("Loading config from %s", self.config_path)
        toml_str = self.config_path.read_text(encoding="utf-8")
        config_dict = tomli.loads(toml_str)

        # Apply migrations if needed
        config_dict = self._migrate(config_dict)

        try:
            return UserConfig.model_validate(config_dict)
        except Exception as e:
            raise ConfigValidationError("config", str(e))

    def delete(self) -> bool:
        """Delete configuration file."""
        if self.exists:
            self.config_path.unlink()
            logger.debug("Config deleted: %s", self.config_path)
            return True
        return False

    def _migrate(self, config_dict: dict) -> dict:
        """Apply schema migrations."""
        version = config_dict.get("version", 1)

        migrations = {
            2: self._migrate_v1_to_v2,
        }

        for target_version in range(version + 1, CURRENT_VERSION + 1):
            if target_version in migrations:
                config_dict = migrations[target_version](config_dict)
                config_dict["version"] = target_version
                logger.info("Migrated config v%d → v%d", target_version - 1, target_version)

        return config_dict

    @staticmethod
    def _migrate_v1_to_v2(config_dict: dict) -> dict:
        """Migrate v1 (single vehicle) to v2 (vehicle list)."""
        if "vehicle" in config_dict and "vehicles" not in config_dict:
            vehicle_data = config_dict.pop("vehicle")
            config_dict["vehicles"] = [
                {
                    "vehicle": vehicle_data,
                    "is_default": True,
                }
            ]
        return config_dict
