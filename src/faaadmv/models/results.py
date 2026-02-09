"""Result models for DMV operations."""

from datetime import date
from decimal import Decimal
from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class StatusType(str, Enum):
    """Registration status types."""

    CURRENT = "current"
    EXPIRING_SOON = "expiring_soon"  # Within 90 days
    PENDING = "pending"
    EXPIRED = "expired"
    HOLD = "hold"


class RegistrationStatus(BaseModel):
    """Result of registration status check."""

    plate: str
    vin_last5: str
    vehicle_description: Optional[str] = None  # e.g., "2019 Honda Accord"
    expiration_date: Optional[date] = None
    status: StatusType
    days_until_expiry: Optional[int] = None
    hold_reason: Optional[str] = None
    status_message: Optional[str] = None  # Raw prose from DMV
    last_updated: Optional[date] = None  # "as of" date from DMV

    @property
    def is_renewable(self) -> bool:
        """Check if vehicle is eligible for online renewal."""
        return self.status in (StatusType.CURRENT, StatusType.EXPIRING_SOON)

    @property
    def status_display(self) -> str:
        """Return formatted status for display."""
        status_map = {
            StatusType.CURRENT: "Current",
            StatusType.EXPIRING_SOON: "Expiring Soon",
            StatusType.PENDING: "Pending",
            StatusType.EXPIRED: "Expired",
            StatusType.HOLD: "Hold",
        }
        return status_map.get(self.status, str(self.status))


class SmogStatus(BaseModel):
    """Smog certification status."""

    passed: bool
    check_date: Optional[date] = None
    station: Optional[str] = None
    certificate_number: Optional[str] = None


class InsuranceStatus(BaseModel):
    """Insurance verification status."""

    verified: bool
    provider: Optional[str] = None
    policy_number: Optional[str] = None


class EligibilityResult(BaseModel):
    """Eligibility verification result."""

    eligible: bool
    smog: SmogStatus
    insurance: InsuranceStatus
    error_message: Optional[str] = None


class FeeItem(BaseModel):
    """Individual fee line item."""

    description: str
    amount: Decimal

    @property
    def amount_display(self) -> str:
        """Format amount for display."""
        return f"${self.amount:.2f}"


class FeeBreakdown(BaseModel):
    """Registration fee breakdown."""

    items: list[FeeItem] = Field(default_factory=list)

    @property
    def total(self) -> Decimal:
        """Calculate total of all fees."""
        return sum(item.amount for item in self.items)

    @property
    def total_display(self) -> str:
        """Format total for display."""
        return f"${self.total:.2f}"


class RenewalResult(BaseModel):
    """Result of successful renewal."""

    success: bool
    confirmation_number: Optional[str] = None
    new_expiration_date: Optional[date] = None
    amount_paid: Optional[Decimal] = None
    receipt_path: Optional[Path] = None
    error_message: Optional[str] = None

    @property
    def amount_display(self) -> str:
        """Format amount paid for display."""
        if self.amount_paid:
            return f"${self.amount_paid:.2f}"
        return ""
