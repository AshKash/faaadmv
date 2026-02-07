"""Owner data models."""

import re

from pydantic import BaseModel, EmailStr, Field, field_validator


class Address(BaseModel):
    """Physical mailing address."""

    street: str = Field(..., min_length=5, max_length=100)
    city: str = Field(..., min_length=2, max_length=50)
    state: str = Field(..., min_length=2, max_length=2)
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")

    @field_validator("state")
    @classmethod
    def normalize_state(cls, v: str) -> str:
        """Normalize state to uppercase."""
        normalized = v.upper()
        if not re.match(r"^[A-Z]{2}$", normalized):
            raise ValueError("State must be a 2-letter code")
        return normalized

    @property
    def formatted(self) -> str:
        """Return formatted single-line address."""
        return f"{self.street}, {self.city}, {self.state} {self.zip_code}"


class OwnerInfo(BaseModel):
    """Vehicle owner personal information."""

    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., description="Phone number (digits only)")
    email: EmailStr
    address: Address

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        """Strip non-digits, validate length."""
        digits = re.sub(r"[^\d]", "", v)
        if len(digits) < 10 or len(digits) > 14:
            raise ValueError("Phone must be 10-14 digits")
        return digits

    @property
    def formatted_phone(self) -> str:
        """Return formatted phone number."""
        digits = self.phone
        if len(digits) == 10:
            return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"
        return digits

    @property
    def masked_email(self) -> str:
        """Return masked email for display."""
        local, domain = self.email.split("@")
        if len(local) <= 2:
            masked_local = local[0] + "*"
        else:
            masked_local = local[0] + "*" * (len(local) - 2) + local[-1]
        return f"{masked_local}@{domain}"
