"""Integration tests for CLI app entry points."""

import pytest
from unittest.mock import patch
from typer.testing import CliRunner

from faaadmv.cli.app import app
from faaadmv.core.config import ConfigManager

runner = CliRunner()


@pytest.fixture
def no_config(tmp_path):
    """Ensure commands see no config by pointing ConfigManager at empty dir."""
    empty_dir = tmp_path / ".config" / "faaadmv"
    manager = ConfigManager(config_dir=empty_dir)
    with (
        patch("faaadmv.cli.commands.register.ConfigManager", return_value=manager),
        patch("faaadmv.cli.commands.status.ConfigManager", return_value=manager),
        patch("faaadmv.cli.commands.renew.ConfigManager", return_value=manager),
        patch("faaadmv.cli.commands.vehicles.ConfigManager", return_value=manager),
        patch("faaadmv.cli.repl.ConfigManager", return_value=manager),
    ):
        yield manager


class TestCLIEntryPoints:
    def test_no_args_enters_repl(self):
        """No args enters the interactive REPL."""
        result = runner.invoke(app, [], input="q\n")
        assert "faaadmv" in result.output

    def test_version_flag(self):
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_version_short_flag(self):
        result = runner.invoke(app, ["-V"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "register" in result.output
        assert "status" in result.output
        assert "vehicles" in result.output
        assert "renew" in result.output

    def test_register_help(self):
        result = runner.invoke(app, ["register", "--help"])
        assert result.exit_code == 0
        assert "--vehicle" in result.output
        assert "--payment" in result.output
        assert "--verify" in result.output
        assert "--reset" in result.output

    def test_status_help(self):
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "--verbose" in result.output

    def test_renew_help(self):
        result = runner.invoke(app, ["renew", "--help"])
        assert result.exit_code == 0
        assert "--dry-run" in result.output
        assert "--headed" in result.output
        assert "--verbose" in result.output

    def test_invalid_command(self):
        result = runner.invoke(app, ["invalid_command"])
        assert result.exit_code != 0


class TestRegisterCommand:
    def test_register_verify_no_config(self, no_config):
        """--verify with no config should fail gracefully with helpful message."""
        result = runner.invoke(app, ["register", "--verify"])
        assert result.exit_code == 1
        # Should tell user to register first
        assert "No configuration found" in result.output or "register" in result.output

    def test_register_reset_decline(self):
        """--reset asks for confirmation and user can decline."""
        result = runner.invoke(app, ["register", "--reset"], input="n\n")
        assert result.exit_code == 0
        assert "Cancelled" in result.output

    def test_register_vehicle_only_no_config(self, no_config):
        """--vehicle with no existing config should fail with helpful message."""
        result = runner.invoke(app, ["register", "--vehicle"])
        assert result.exit_code == 1
        assert "No existing configuration" in result.output or "register" in result.output

    def test_register_payment_only_no_config(self, no_config):
        """--payment with no existing config should fail with helpful message."""
        result = runner.invoke(app, ["register", "--payment"])
        assert result.exit_code == 1
        assert "No existing configuration" in result.output or "register" in result.output


class TestStatusCommand:
    def test_status_no_config(self, no_config):
        """Status with no config should fail with helpful message."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_status_verbose_no_config(self, no_config):
        result = runner.invoke(app, ["status", "--verbose"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output


class TestRenewCommand:
    def test_renew_no_config(self, no_config):
        """Renew with no config should fail with helpful message."""
        result = runner.invoke(app, ["renew"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_renew_dry_run_no_config(self, no_config):
        result = runner.invoke(app, ["renew", "--dry-run"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output


class TestREPL:
    def test_repl_no_config_shows_add_option(self, no_config):
        """REPL with no config shows 'Add a vehicle' option."""
        result = runner.invoke(app, [], input="q\n")
        assert "No vehicles registered" in result.output
        assert "Add a vehicle" in result.output

    def test_repl_quit(self):
        """REPL exits cleanly on 'q'."""
        result = runner.invoke(app, [], input="q\n")
        assert "Goodbye" in result.output

    def test_repl_add_vehicle_flow(self, tmp_path, mock_keyring):
        """REPL: add vehicle -> shows in dashboard."""
        config_dir = tmp_path / ".config" / "faaadmv"
        with patch("faaadmv.cli.repl.ConfigManager") as MockCM:
            real_manager = ConfigManager(config_dir=config_dir)
            MockCM.return_value = real_manager

            # Add vehicle flow: a -> plate -> vin -> nickname -> q
            result = runner.invoke(app, [], input="\n".join([
                "a",            # add vehicle
                "8ABC123",      # plate
                "12345",        # VIN
                "",             # nickname (skip)
                "q",            # quit
            ]))

        assert result.exit_code == 0, f"REPL failed: {result.output}"
        assert "8ABC123" in result.output
        assert "Vehicle 8ABC123 added" in result.output


class TestVehiclesCommand:
    def test_vehicles_no_config(self, no_config):
        """Vehicles with no config should fail with helpful message."""
        result = runner.invoke(app, ["vehicles"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_vehicles_help(self):
        result = runner.invoke(app, ["vehicles", "--help"])
        assert result.exit_code == 0
        assert "--add" in result.output
        assert "--remove" in result.output
        assert "--default" in result.output

    def test_vehicles_add_no_config(self, no_config):
        result = runner.invoke(app, ["vehicles", "--add"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output
