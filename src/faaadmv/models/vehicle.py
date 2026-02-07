"""Vehicle data model."""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class VehicleInfo(BaseModel):
    """Vehicle identification data."""

    plate: str = Field(
        ...,
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
        """Normalize plate to uppercase, alphanumeric only.

        Strips dashes, spaces, and other non-alphanumeric characters
        before checking length.
        """
        normalized = re.sub(r"[^A-Z0-9]", "", v.upper())
        if len(normalized) < 2:
            raise ValueError("Plate must have at least 2 characters")
        if len(normalized) > 8:
            raise ValueError("Plate must have at most 8 characters")
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


class VehicleEntry(BaseModel):
    """A vehicle in the user's vehicle list (v2 schema)."""

    vehicle: VehicleInfo
    nickname: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Optional friendly name, e.g. 'My Tesla'",
    )
    is_default: bool = Field(default=False)
    added_at: datetime = Field(default_factory=datetime.now)

    @property
    def display_name(self) -> str:
        """Friendly display name: nickname or plate."""
        return self.nickname or self.vehicle.plate

    @property
    def plate(self) -> str:
        """Shortcut to vehicle.plate."""
        return self.vehicle.plate

    @property
    def vin_last5(self) -> str:
        """Shortcut to vehicle.vin_last5."""
        return self.vehicle.vin_last5
