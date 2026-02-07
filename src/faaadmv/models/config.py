"""User configuration model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from faaadmv.models.owner import OwnerInfo
from faaadmv.models.payment import PaymentInfo
from faaadmv.models.vehicle import VehicleInfo


class UserConfig(BaseModel):
    """Complete user configuration."""

    # Schema version for migrations
    version: int = Field(default=1, description="Config schema version")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Required data
    vehicle: VehicleInfo
    owner: OwnerInfo

    # Payment stored separately in keychain, populated at runtime
    # Excluded from serialization
    payment: Optional[PaymentInfo] = Field(default=None, exclude=True)

    # Provider settings
    state: str = Field(default="CA", pattern=r"^[A-Z]{2}$")

    def model_post_init(self, __context: object) -> None:
        """Update timestamp on any modification."""
        object.__setattr__(self, "updated_at", datetime.now())

    def with_payment(self, payment: PaymentInfo) -> "UserConfig":
        """Return new config with payment info attached."""
        return self.model_copy(update={"payment": payment})

    @property
    def has_payment(self) -> bool:
        """Check if payment info is loaded."""
        return self.payment is not None

    @property
    def summary(self) -> dict[str, str]:
        """Return summary dict for display."""
        return {
            "plate": self.vehicle.plate,
            "vin": self.vehicle.masked_vin,
            "owner": self.owner.full_name,
            "email": self.owner.masked_email,
            "state": self.state,
        }
