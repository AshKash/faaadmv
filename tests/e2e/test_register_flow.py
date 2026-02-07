"""E2E test: full register → verify → reset flow.

This is the P0 happy path. If this doesn't work, nothing works.
"""

import pytest
from unittest.mock import patch
from typer.testing import CliRunner

from faaadmv.cli.app import app
from faaadmv.core.config import ConfigManager

runner = CliRunner()

# Simulated user input for full registration (with payment)
REGISTER_INPUT = "\n".join([
    "8ABC123",           # plate
    "12345",             # vin last 5
    "Jane Doe",          # full name
    "5551234567",        # phone
    "jane@example.com",  # email
    "123 Main Street",   # street
    "Los Angeles",       # city
    "CA",                # state
    "90001",             # zip
    "y",                 # yes, add payment
    "4242424242424242",  # card number
    "12",                # exp month
    "27",                # exp year
    "123",               # cvv
    "90001",             # billing zip
    "testpass1234",      # passphrase
    "testpass1234",      # confirm passphrase
])

# Simulated user input for registration without payment
REGISTER_INPUT_NO_PAYMENT = "\n".join([
    "8ABC123",           # plate
    "12345",             # vin last 5
    "Jane Doe",          # full name
    "5551234567",        # phone
    "jane@example.com",  # email
    "123 Main Street",   # street
    "Los Angeles",       # city
    "CA",                # state
    "90001",             # zip
    "n",                 # no payment
    "testpass1234",      # passphrase
    "testpass1234",      # confirm passphrase
])


class TestRegisterFlow:
    """P0: Can a user register, verify, and reset?"""

    def test_full_register_saves_config(self, tmp_path, mock_keyring):
        """Core flow: faaadmv register with all fields → config saved."""
        config_dir = tmp_path / ".config" / "faaadmv"

        with patch("faaadmv.cli.commands.register.ConfigManager") as MockCM:
            real_manager = ConfigManager(config_dir=config_dir)
            MockCM.return_value = real_manager

            result = runner.invoke(app, ["register"], input=REGISTER_INPUT)

        print("OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Register failed with exit code {result.exit_code}"
        assert "Configuration saved" in result.output

        # Verify the file was actually created
        assert real_manager.exists, "Config file was not created on disk"

        # Verify we can load it back
        loaded = real_manager.load("testpass1234")
        assert loaded.vehicle.plate == "8ABC123"
        assert loaded.vehicle.vin_last5 == "12345"
        assert loaded.owner.full_name == "Jane Doe"
        assert loaded.owner.email == "jane@example.com"

    def test_register_then_verify(self, tmp_path, mock_keyring):
        """Core flow: register → verify shows saved data."""
        config_dir = tmp_path / ".config" / "faaadmv"

        with patch("faaadmv.cli.commands.register.ConfigManager") as MockCM:
            real_manager = ConfigManager(config_dir=config_dir)
            MockCM.return_value = real_manager

            # Step 1: Register
            result = runner.invoke(app, ["register"], input=REGISTER_INPUT)
            assert result.exit_code == 0, f"Register failed: {result.output}"

            # Step 2: Verify
            result = runner.invoke(
                app,
                ["register", "--verify"],
                input="testpass1234\n",
            )

        print("VERIFY OUTPUT:", result.output)
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)

        assert result.exit_code == 0, f"Verify failed with exit code {result.exit_code}"
        assert "8ABC123" in result.output
        assert "Jane Doe" in result.output
        assert "All fields valid" in result.output

    def test_register_then_reset(self, tmp_path, mock_keyring):
        """Core flow: register → reset deletes everything."""
        config_dir = tmp_path / ".config" / "faaadmv"

        with patch("faaadmv.cli.commands.register.ConfigManager") as MockCM:
            real_manager = ConfigManager(config_dir=config_dir)
            MockCM.return_value = real_manager

            # Step 1: Register
            result = runner.invoke(app, ["register"], input=REGISTER_INPUT)
            assert result.exit_code == 0
            assert real_manager.exists

            # Step 2: Reset (confirm yes)
            result = runner.invoke(
                app,
                ["register", "--reset"],
                input="y\n",
            )

        print("RESET OUTPUT:", result.output)
        assert result.exit_code == 0
        assert "deleted" in result.output.lower() or "Configuration" in result.output
        assert not real_manager.exists, "Config file still exists after reset"

    def test_register_without_payment(self, tmp_path, mock_keyring):
        """Register without payment info — should still succeed."""
        config_dir = tmp_path / ".config" / "faaadmv"

        with patch("faaadmv.cli.commands.register.ConfigManager") as MockCM:
            real_manager = ConfigManager(config_dir=config_dir)
            MockCM.return_value = real_manager

            result = runner.invoke(app, ["register"], input=REGISTER_INPUT_NO_PAYMENT)

        assert result.exit_code == 0, f"Register failed: {result.output}"
        assert "Configuration saved" in result.output

        loaded = real_manager.load("testpass1234")
        assert loaded.vehicle.plate == "8ABC123"
        assert loaded.owner.full_name == "Jane Doe"

    def test_verify_wrong_passphrase(self, tmp_path, mock_keyring):
        """Verify with wrong passphrase gives clear error."""
        config_dir = tmp_path / ".config" / "faaadmv"

        with patch("faaadmv.cli.commands.register.ConfigManager") as MockCM:
            real_manager = ConfigManager(config_dir=config_dir)
            MockCM.return_value = real_manager

            # Register
            result = runner.invoke(app, ["register"], input=REGISTER_INPUT)
            assert result.exit_code == 0

            # Verify with wrong pass
            result = runner.invoke(
                app,
                ["register", "--verify"],
                input="wrongpassword\n",
            )

        assert result.exit_code == 1
        assert "passphrase" in result.output.lower() or "Wrong" in result.output
