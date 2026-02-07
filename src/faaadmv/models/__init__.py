"""Data models for faaadmv."""

from faaadmv.models.config import UserConfig
from faaadmv.models.owner import Address, OwnerInfo
from faaadmv.models.payment import PaymentInfo
from faaadmv.models.results import (
    EligibilityResult,
    FeeBreakdown,
    FeeItem,
    InsuranceStatus,
    RegistrationStatus,
    RenewalResult,
    SmogStatus,
    StatusType,
)
from faaadmv.models.vehicle import VehicleEntry, VehicleInfo

__all__ = [
    # Config
    "UserConfig",
    # Vehicle
    "VehicleEntry",
    "VehicleInfo",
    # Owner
    "OwnerInfo",
    "Address",
    # Payment
    "PaymentInfo",
    # Results
    "RegistrationStatus",
    "StatusType",
    "EligibilityResult",
    "SmogStatus",
    "InsuranceStatus",
    "FeeBreakdown",
    "FeeItem",
    "RenewalResult",
]
