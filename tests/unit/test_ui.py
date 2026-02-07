"""Tests for CLI UI helpers."""

from faaadmv.cli.ui import (
    create_config_table,
    create_fee_table,
    error_panel,
    format_phone,
    info_panel,
    masked_value,
    success_panel,
    warning_panel,
)


class TestMaskedValue:
    def test_long_value(self):
        assert masked_value("4242424242424242") == "************4242"

    def test_short_value(self):
        assert masked_value("123") == "***"

    def test_exact_visible_chars(self):
        assert masked_value("1234") == "****"

    def test_custom_visible_chars(self):
        assert masked_value("4242424242424242", visible_chars=6) == "**********424242"

    def test_empty_string(self):
        assert masked_value("") == ""


class TestFormatPhone:
    def test_10_digit(self):
        assert format_phone("5551234567") == "(555) 123-4567"

    def test_non_10_digit(self):
        assert format_phone("15551234567") == "15551234567"

    def test_short_number(self):
        assert format_phone("12345") == "12345"


class TestPanels:
    def test_success_panel_renderable(self):
        panel = success_panel("It worked!")
        assert panel is not None

    def test_error_panel_renderable(self):
        panel = error_panel("Something failed")
        assert panel is not None

    def test_error_panel_with_details(self):
        panel = error_panel("Failed", details="More info here")
        assert panel is not None

    def test_warning_panel_renderable(self):
        panel = warning_panel("Watch out!")
        assert panel is not None

    def test_info_panel_renderable(self):
        panel = info_panel("Some info", title="Info")
        assert panel is not None


class TestCreateConfigTable:
    def test_basic_config(self):
        table = create_config_table({
            "plate": "8ABC123",
            "vin": "***45",
            "owner": "Jane Doe",
            "email": "j**e@example.com",
            "card": "****4242",
        })
        assert table is not None

    def test_missing_fields(self):
        table = create_config_table({})
        assert table is not None  # Should show N/A


class TestCreateFeeTable:
    def test_basic_fees(self):
        table = create_fee_table([
            ("Registration", 168.00),
            ("CHP Fee", 32.00),
        ])
        assert table is not None

    def test_empty_fees(self):
        table = create_fee_table([])
        assert table is not None
