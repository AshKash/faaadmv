"""Tests for VehicleInfo model."""

import pytest
from pydantic import ValidationError

from faaadmv.models.vehicle import VehicleInfo


class TestVehicleInfoValid:
    def test_basic_valid(self):
        v = VehicleInfo(plate="8ABC123", vin_last5="12345")
        assert v.plate == "8ABC123"
        assert v.vin_last5 == "12345"

    def test_plate_uppercase_normalization(self):
        v = VehicleInfo(plate="abc123", vin_last5="12345")
        assert v.plate == "ABC123"

    def test_plate_strips_dashes_short_input(self):
        # Dashes within max_length=8 work fine
        v = VehicleInfo(plate="8-ABC12", vin_last5="12345")
        assert v.plate == "8ABC12"

    def test_plate_strips_dashes(self):
        # BUG-001 FIXED: normalization now strips dashes before length check
        v = VehicleInfo(plate="8-ABC-123", vin_last5="12345")
        assert v.plate == "8ABC123"

    def test_plate_strips_spaces(self):
        # BUG-002 FIXED: normalization now strips spaces before length check
        v = VehicleInfo(plate="8 ABC 123", vin_last5="12345")
        assert v.plate == "8ABC123"

    def test_plate_minimum_length(self):
        v = VehicleInfo(plate="AB", vin_last5="12345")
        assert v.plate == "AB"

    def test_vin_all_digits(self):
        v = VehicleInfo(plate="TEST", vin_last5="99999")
        assert v.vin_last5 == "99999"

    def test_vin_alphanumeric(self):
        v = VehicleInfo(plate="TEST", vin_last5="A1B2C")
        assert v.vin_last5 == "A1B2C"

    def test_vin_lowercase_normalized(self):
        v = VehicleInfo(plate="TEST", vin_last5="abcde")
        assert v.vin_last5 == "ABCDE"

    def test_masked_vin(self):
        v = VehicleInfo(plate="8ABC123", vin_last5="12345")
        assert v.masked_vin == "***45"


class TestVehicleInfoInvalid:
    def test_plate_too_short_after_strip(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="-", vin_last5="12345")

    def test_plate_empty(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="", vin_last5="12345")

    def test_plate_too_long(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABCDEFGHIJK", vin_last5="12345")

    def test_vin_too_short(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABC123", vin_last5="1234")

    def test_vin_too_long(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABC123", vin_last5="123456")

    def test_vin_contains_I(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABC123", vin_last5="1I345")

    def test_vin_contains_O(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABC123", vin_last5="1O345")

    def test_vin_contains_Q(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABC123", vin_last5="1Q345")

    def test_vin_special_chars(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABC123", vin_last5="12#45")

    def test_missing_plate(self):
        with pytest.raises(ValidationError):
            VehicleInfo(vin_last5="12345")

    def test_missing_vin(self):
        with pytest.raises(ValidationError):
            VehicleInfo(plate="ABC123")
