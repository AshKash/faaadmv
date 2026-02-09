"""User configuration model."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from faaadmv.models.owner import OwnerInfo
from faaadmv.models.payment import PaymentInfo
from faaadmv.models.vehicle import VehicleEntry, VehicleInfo


class UserConfig(BaseModel):
    """Complete user configuration (v2 schema with multi-vehicle support)."""

    # Schema version for migrations
    version: int = Field(default=2, description="Config schema version")

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    # Vehicle list (v2) — at least one required
    vehicles: list[VehicleEntry] = Field(
        default_factory=list,
        description="Registered vehicles",
    )

    # Owner info — optional, only needed if DMV requires it
    owner: Optional[OwnerInfo] = None

    # Payment stored separately in keychain, populated at runtime
    # Excluded from serialization
    payment: Optional[PaymentInfo] = Field(default=None, exclude=True)

    # Provider settings
    state: str = Field(default="CA", pattern=r"^[A-Z]{2}$")

    @model_validator(mode="after")
    def validate_vehicles(self) -> "UserConfig":
        """Ensure at least one vehicle exists."""
        if not self.vehicles:
            raise ValueError("At least one vehicle is required")
        return self

    def model_post_init(self, __context: object) -> None:
        """Update timestamp on any modification."""
        object.__setattr__(self, "updated_at", datetime.now())

    # --- Backward compatibility ---

    @property
    def vehicle(self) -> VehicleInfo:
        """Return the default vehicle's VehicleInfo (backward compat)."""
        return self.default_vehicle.vehicle

    # --- Vehicle management ---

    @property
    def default_vehicle(self) -> VehicleEntry:
        """Return the default vehicle entry."""
        for entry in self.vehicles:
            if entry.is_default:
                return entry
        # Fallback: first vehicle
        return self.vehicles[0]

    def get_vehicle(self, plate: str) -> Optional[VehicleEntry]:
        """Find a vehicle by plate number."""
        normalized = plate.upper().replace("-", "").replace(" ", "")
        for entry in self.vehicles:
            if entry.vehicle.plate == normalized:
                return entry
        return None

    def add_vehicle(
        self,
        vehicle: VehicleInfo,
        nickname: Optional[str] = None,
        is_default: bool = False,
    ) -> "UserConfig":
        """Return new config with vehicle added."""
        entry = VehicleEntry(
            vehicle=vehicle,
            nickname=nickname,
            is_default=is_default,
        )

        new_vehicles = list(self.vehicles)

        # If this is the only vehicle or marked default, clear other defaults
        if is_default or len(new_vehicles) == 0:
            new_vehicles = [
                v.model_copy(update={"is_default": False}) for v in new_vehicles
            ]
            entry = entry.model_copy(update={"is_default": True})

        new_vehicles.append(entry)
        return self.model_copy(update={"vehicles": new_vehicles})

    def remove_vehicle(self, plate: str) -> "UserConfig":
        """Return new config with vehicle removed."""
        normalized = plate.upper().replace("-", "").replace(" ", "")
        new_vehicles = [v for v in self.vehicles if v.vehicle.plate != normalized]

        if len(new_vehicles) == len(self.vehicles):
            raise ValueError(f"Vehicle with plate '{plate}' not found")

        if len(new_vehicles) == 0:
            raise ValueError("Cannot remove the last vehicle")

        # If we removed the default, promote the first remaining
        if not any(v.is_default for v in new_vehicles):
            new_vehicles[0] = new_vehicles[0].model_copy(update={"is_default": True})

        return self.model_copy(update={"vehicles": new_vehicles})

    def set_default(self, plate: str) -> "UserConfig":
        """Return new config with given plate set as default."""
        normalized = plate.upper().replace("-", "").replace(" ", "")
        found = False
        new_vehicles = []

        for v in self.vehicles:
            if v.vehicle.plate == normalized:
                new_vehicles.append(v.model_copy(update={"is_default": True}))
                found = True
            else:
                new_vehicles.append(v.model_copy(update={"is_default": False}))

        if not found:
            raise ValueError(f"Vehicle with plate '{plate}' not found")

        return self.model_copy(update={"vehicles": new_vehicles})

    # --- Payment ---

    def with_payment(self, payment: PaymentInfo) -> "UserConfig":
        """Return new config with payment info attached."""
        return self.model_copy(update={"payment": payment})
