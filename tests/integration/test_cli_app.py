"""Integration tests for CLI app entry points."""

import pytest
from typer.testing import CliRunner

from faaadmv.cli.app import app

runner = CliRunner()


class TestCLIEntryPoints:
    def test_no_args_shows_help(self):
        """no_args_is_help=True causes exit code 2 (standard Click/Typer behavior)."""
        result = runner.invoke(app, [])
        # Typer/Click returns exit code 2 for "missing required" / help-shown
        assert result.exit_code == 2
        assert "Usage" in result.output

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
    def test_register_verify_no_config(self):
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

    def test_register_vehicle_only_no_config(self):
        """--vehicle with no existing config should fail with helpful message."""
        result = runner.invoke(app, ["register", "--vehicle"])
        assert result.exit_code == 1
        assert "No existing configuration" in result.output or "register" in result.output

    def test_register_payment_only_no_config(self):
        """--payment with no existing config should fail with helpful message."""
        result = runner.invoke(app, ["register", "--payment"])
        assert result.exit_code == 1
        assert "No existing configuration" in result.output or "register" in result.output


class TestStatusCommand:
    def test_status_no_config(self):
        """Status with no config should fail with helpful message."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_status_verbose_no_config(self):
        result = runner.invoke(app, ["status", "--verbose"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output


class TestRenewCommand:
    def test_renew_no_config(self):
        """Renew with no config should fail with helpful message."""
        result = runner.invoke(app, ["renew"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output

    def test_renew_dry_run_no_config(self):
        result = runner.invoke(app, ["renew", "--dry-run"])
        assert result.exit_code == 1
        assert "No configuration found" in result.output
