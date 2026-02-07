"""Vehicle data model."""

import re

from pydantic import BaseModel, Field, field_validator


class VehicleInfo(BaseModel):
    """Vehicle identification data."""

    plate: str = Field(
        ...,
        min_length=2,
        max_length=8,
        description="License plate number",
    )
    vin_last5: str = Field(
        ...,
        min_length=5,
        max_length=5,
        description="Last 5 characters of VIN",
    )

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, v: str) -> str:
        """Normalize plate to uppercase, alphanumeric only."""
        normalized = re.sub(r"[^A-Z0-9]", "", v.upper())
        if len(normalized) < 2:
            raise ValueError("Plate must have at least 2 characters")
        return normalized

    @field_validator("vin_last5")
    @classmethod
    def validate_vin(cls, v: str) -> str:
        """Validate and normalize VIN characters."""
        normalized = v.upper()
        # VIN cannot contain I, O, Q
        if not re.match(r"^[A-HJ-NPR-Z0-9]{5}$", normalized):
            raise ValueError(
                "VIN must be 5 alphanumeric characters (I, O, Q not allowed)"
            )
        return normalized

    @property
    def masked_vin(self) -> str:
        """Return masked VIN for display."""
        return f"***{self.vin_last5[-2:]}"
