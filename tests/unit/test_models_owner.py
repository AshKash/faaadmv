"""Tests for OwnerInfo and Address models."""

import pytest
from pydantic import ValidationError

from faaadmv.models.owner import Address, OwnerInfo


class TestAddress:
    def test_valid_address(self):
        a = Address(street="123 Main St", city="Los Angeles", state="CA", zip_code="90001")
        assert a.state == "CA"
        assert a.zip_code == "90001"

    def test_state_normalized_uppercase(self):
        a = Address(street="123 Main St", city="Los Angeles", state="ca", zip_code="90001")
        assert a.state == "CA"

    def test_formatted_address(self):
        a = Address(street="123 Main St", city="Los Angeles", state="CA", zip_code="90001")
        assert a.formatted == "123 Main St, Los Angeles, CA 90001"

    def test_zip_with_extension(self):
        a = Address(street="123 Main St", city="Los Angeles", state="CA", zip_code="90001-1234")
        assert a.zip_code == "90001-1234"

    def test_street_too_short(self):
        with pytest.raises(ValidationError):
            Address(street="Hi", city="LA", state="CA", zip_code="90001")

    def test_invalid_zip(self):
        with pytest.raises(ValidationError):
            Address(street="123 Main St", city="LA", state="CA", zip_code="9000")

    def test_invalid_zip_letters(self):
        with pytest.raises(ValidationError):
            Address(street="123 Main St", city="LA", state="CA", zip_code="ABCDE")

    def test_state_three_letters(self):
        with pytest.raises(ValidationError):
            Address(street="123 Main St", city="LA", state="CAL", zip_code="90001")

    def test_state_one_letter(self):
        with pytest.raises(ValidationError):
            Address(street="123 Main St", city="LA", state="C", zip_code="90001")


class TestOwnerInfo:
    @pytest.fixture
    def valid_address(self):
        return Address(street="123 Main St", city="Los Angeles", state="CA", zip_code="90001")

    def test_valid_owner(self, valid_address):
        o = OwnerInfo(
            full_name="Jane Doe",
            phone="5551234567",
            email="jane@example.com",
            address=valid_address,
        )
        assert o.full_name == "Jane Doe"
        assert o.phone == "5551234567"

    def test_phone_strips_formatting(self, valid_address):
        o = OwnerInfo(
            full_name="Jane Doe",
            phone="(555) 123-4567",
            email="jane@example.com",
            address=valid_address,
        )
        assert o.phone == "5551234567"

    def test_phone_strips_dashes_and_spaces(self, valid_address):
        o = OwnerInfo(
            full_name="Jane Doe",
            phone="555-123-4567",
            email="jane@example.com",
            address=valid_address,
        )
        assert o.phone == "5551234567"

    def test_formatted_phone(self, valid_address):
        o = OwnerInfo(
            full_name="Jane Doe",
            phone="5551234567",
            email="jane@example.com",
            address=valid_address,
        )
        assert o.formatted_phone == "(555) 123-4567"

    def test_masked_email(self, valid_address):
        o = OwnerInfo(
            full_name="Jane Doe",
            phone="5551234567",
            email="jane@example.com",
            address=valid_address,
        )
        # "jane" -> "j**e"
        assert o.masked_email == "j**e@example.com"

    def test_masked_email_short_local(self, valid_address):
        o = OwnerInfo(
            full_name="Jane Doe",
            phone="5551234567",
            email="ab@example.com",
            address=valid_address,
        )
        assert o.masked_email == "a*@example.com"

    def test_phone_too_short(self, valid_address):
        with pytest.raises(ValidationError):
            OwnerInfo(
                full_name="Jane Doe",
                phone="12345",
                email="jane@example.com",
                address=valid_address,
            )

    def test_invalid_email(self, valid_address):
        with pytest.raises(ValidationError):
            OwnerInfo(
                full_name="Jane Doe",
                phone="5551234567",
                email="not-an-email",
                address=valid_address,
            )

    def test_name_too_short(self, valid_address):
        with pytest.raises(ValidationError):
            OwnerInfo(
                full_name="J",
                phone="5551234567",
                email="jane@example.com",
                address=valid_address,
            )
