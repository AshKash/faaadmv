# faaadmv Data Models

## Overview

All data models use Pydantic v2 for validation, serialization, and type safety.

## Core Models

### VehicleInfo

```python
from pydantic import BaseModel, Field, field_validator
import re

class VehicleInfo(BaseModel):
    """Vehicle identification data."""

    plate: str = Field(
        ...,
        min_length=2,
        max_length=8,
        description="License plate number"
    )
    vin_last5: str = Field(
        ...,
        min_length=5,
        max_length=5,
        pattern=r"^[A-HJ-NPR-Z0-9]{5}$",
        description="Last 5 characters of VIN"
    )

    @field_validator("plate")
    @classmethod
    def normalize_plate(cls, v: str) -> str:
        """Normalize plate to uppercase, no spaces."""
        return re.sub(r"[^A-Z0-9]", "", v.upper())

    @field_validator("vin_last5")
    @classmethod
    def normalize_vin(cls, v: str) -> str:
        """Normalize VIN to uppercase."""
        return v.upper()
```

### OwnerInfo

```python
from pydantic import BaseModel, Field, EmailStr, field_validator
import re

class Address(BaseModel):
    """Physical mailing address."""

    street: str = Field(..., min_length=5, max_length=100)
    city: str = Field(..., min_length=2, max_length=50)
    state: str = Field(..., min_length=2, max_length=2, pattern=r"^[A-Z]{2}$")
    zip_code: str = Field(..., pattern=r"^\d{5}(-\d{4})?$")

    @field_validator("state")
    @classmethod
    def normalize_state(cls, v: str) -> str:
        return v.upper()

class OwnerInfo(BaseModel):
    """Vehicle owner personal information."""

    full_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., pattern=r"^\+?1?\d{10,14}$")
    email: EmailStr
    address: Address

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, v: str) -> str:
        """Strip non-digits, keep only numbers."""
        return re.sub(r"[^\d]", "", v)
```

### PaymentInfo

```python
from pydantic import BaseModel, Field, SecretStr, field_validator
from datetime import date

class PaymentInfo(BaseModel):
    """Payment card information. Stored in OS keychain."""

    card_number: SecretStr = Field(..., description="16-digit card number")
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2024, le=2099)
    cvv: SecretStr = Field(..., description="3-4 digit security code")
    billing_zip: str = Field(..., pattern=r"^\d{5}$")

    @field_validator("card_number")
    @classmethod
    def validate_card_luhn(cls, v: SecretStr) -> SecretStr:
        """Validate card number using Luhn algorithm."""
        digits = v.get_secret_value().replace(" ", "").replace("-", "")
        if not digits.isdigit() or len(digits) not in (15, 16):
            raise ValueError("Invalid card number format")
        if not cls._luhn_check(digits):
            raise ValueError("Invalid card number (Luhn check failed)")
        return v

    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Luhn algorithm implementation."""
        digits = [int(d) for d in card_number]
        odd_digits = digits[-1::-2]
        even_digits = digits[-2::-2]
        checksum = sum(odd_digits)
        for d in even_digits:
            checksum += sum(divmod(d * 2, 10))
        return checksum % 10 == 0

    @property
    def is_expired(self) -> bool:
        """Check if card is expired."""
        today = date.today()
        return (self.expiry_year, self.expiry_month) < (today.year, today.month)

    @property
    def masked_number(self) -> str:
        """Return masked card number for display."""
        full = self.card_number.get_secret_value()
        return f"****{full[-4:]}"

    @property
    def expiry_display(self) -> str:
        """Format expiry for display."""
        return f"{self.expiry_month:02d}/{self.expiry_year % 100:02d}"
```

### UserConfig

**v1 (current):** Single vehicle per config.

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserConfig(BaseModel):
    """Complete user configuration (v1 — single vehicle)."""

    version: int = Field(default=1, description="Config schema version")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    vehicle: VehicleInfo
    owner: OwnerInfo

    # Payment stored separately in keychain, not in config file
    # This field is transient, populated at runtime
    payment: Optional[PaymentInfo] = Field(default=None, exclude=True)

    # Provider settings
    state: str = Field(default="CA", pattern=r"^[A-Z]{2}$")

    def model_post_init(self, __context) -> None:
        """Update timestamp on any change."""
        self.updated_at = datetime.now()
```

### UserConfig v2 (planned — multi-vehicle)

```python
class VehicleEntry(BaseModel):
    """A registered vehicle with optional nickname."""

    vehicle: VehicleInfo
    nickname: Optional[str] = Field(default=None, max_length=30)
    is_default: bool = Field(default=False)
    added_at: datetime = Field(default_factory=datetime.now)

class UserConfig(BaseModel):
    """Complete user configuration (v2 — multi-vehicle)."""

    version: int = Field(default=2)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    vehicles: list[VehicleEntry] = Field(default_factory=list)
    owner: OwnerInfo

    payment: Optional[PaymentInfo] = Field(default=None, exclude=True)
    state: str = Field(default="CA", pattern=r"^[A-Z]{2}$")

    @property
    def default_vehicle(self) -> Optional[VehicleEntry]:
        """Get the default vehicle, or the only one, or None."""
        if len(self.vehicles) == 1:
            return self.vehicles[0]
        for v in self.vehicles:
            if v.is_default:
                return v
        return None

    def get_vehicle(self, plate: str) -> Optional[VehicleEntry]:
        """Look up vehicle by plate."""
        plate_upper = plate.upper()
        for v in self.vehicles:
            if v.vehicle.plate == plate_upper:
                return v
        return None

    def add_vehicle(self, vehicle: VehicleInfo, nickname: str = None) -> None:
        """Add a vehicle. First vehicle becomes default."""
        is_default = len(self.vehicles) == 0
        self.vehicles.append(VehicleEntry(
            vehicle=vehicle, nickname=nickname, is_default=is_default
        ))

    def remove_vehicle(self, plate: str) -> bool:
        """Remove a vehicle by plate. Returns True if found."""
        plate_upper = plate.upper()
        before = len(self.vehicles)
        self.vehicles = [v for v in self.vehicles if v.vehicle.plate != plate_upper]
        # If we removed the default, promote the first remaining
        if self.vehicles and not any(v.is_default for v in self.vehicles):
            self.vehicles[0].is_default = True
        return len(self.vehicles) < before
```

## Result Models

### RegistrationStatus

```python
from pydantic import BaseModel
from enum import Enum
from typing import Optional
from datetime import date

class StatusType(str, Enum):
    CURRENT = "current"
    EXPIRING_SOON = "expiring_soon"  # Within 90 days
    PENDING = "pending"
    EXPIRED = "expired"
    HOLD = "hold"

class RegistrationStatus(BaseModel):
    """Result of status check."""

    plate: str
    vin_last5: str
    vehicle_description: Optional[str] = None  # "2019 Honda Accord"
    expiration_date: date
    status: StatusType
    days_until_expiry: int
    hold_reason: Optional[str] = None

    @property
    def is_renewable(self) -> bool:
        """Check if vehicle is eligible for online renewal."""
        return self.status in (StatusType.CURRENT, StatusType.EXPIRING_SOON)
```

### EligibilityResult

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date

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
```

### FeeBreakdown

```python
from pydantic import BaseModel
from decimal import Decimal
from typing import List

class FeeItem(BaseModel):
    """Individual fee line item."""
    description: str
    amount: Decimal

class FeeBreakdown(BaseModel):
    """Registration fee breakdown."""
    items: List[FeeItem]

    @property
    def total(self) -> Decimal:
        return sum(item.amount for item in self.items)

    @property
    def total_display(self) -> str:
        return f"${self.total:.2f}"
```

### RenewalResult

```python
from pydantic import BaseModel
from typing import Optional
from datetime import date
from pathlib import Path

class RenewalResult(BaseModel):
    """Result of successful renewal."""
    success: bool
    confirmation_number: Optional[str] = None
    new_expiration_date: Optional[date] = None
    amount_paid: Optional[Decimal] = None
    receipt_path: Optional[Path] = None
    error_message: Optional[str] = None
```

## Serialization

### Config File Format

The config is serialized to TOML before encryption.

**v1 (current — single vehicle):**

```toml
version = 1
created_at = "2026-02-07T10:30:00"
updated_at = "2026-02-07T10:30:00"
state = "CA"

[vehicle]
plate = "8ABC123"
vin_last5 = "12345"

[owner]
full_name = "Jane Doe"
phone = "5551234567"
email = "jane@example.com"

[owner.address]
street = "123 Main Street"
city = "Los Angeles"
state = "CA"
zip_code = "90001"
```

**v2 (planned — multi-vehicle):**

```toml
version = 2
created_at = "2026-02-07T10:30:00"
updated_at = "2026-02-07T10:30:00"
state = "CA"

[[vehicles]]
nickname = "Honda"
is_default = true
added_at = "2026-02-07T10:30:00"

[vehicles.vehicle]
plate = "8ABC123"
vin_last5 = "12345"

[[vehicles]]
nickname = "Tesla"
is_default = false
added_at = "2026-03-15T09:00:00"

[vehicles.vehicle]
plate = "7XYZ999"
vin_last5 = "67890"

[owner]
full_name = "Jane Doe"
phone = "5551234567"
email = "jane@example.com"

[owner.address]
street = "123 Main Street"
city = "Los Angeles"
state = "CA"
zip_code = "90001"
```

### Keychain Keys

Payment data stored in OS keychain with these service/key names:

| Service | Key | Value |
|---------|-----|-------|
| `faaadmv` | `card_number` | Full card number |
| `faaadmv` | `card_expiry` | `MM/YY` format |
| `faaadmv` | `card_cvv` | 3-4 digit CVV |
| `faaadmv` | `billing_zip` | 5-digit ZIP |

## Migration Strategy

Config schema versioning supports future migrations:

```python
MIGRATIONS = {
    1: lambda config: config,  # Initial version (no-op)
    2: _migrate_v1_to_v2,      # Single vehicle → vehicle list
}

def _migrate_v1_to_v2(config: dict) -> dict:
    """Migrate v1 (single vehicle) to v2 (multi-vehicle).

    Wraps the single vehicle in a vehicles list, sets it as default.
    """
    vehicle = config.pop("vehicle", None)
    if vehicle:
        config["vehicles"] = [
            {
                "vehicle": vehicle,
                "nickname": None,
                "is_default": True,
                "added_at": config.get("created_at", datetime.now().isoformat()),
            }
        ]
    else:
        config["vehicles"] = []
    return config

def migrate_config(config: dict) -> dict:
    """Apply migrations up to current version."""
    current = config.get("version", 1)
    for version in range(current + 1, CURRENT_VERSION + 1):
        config = MIGRATIONS[version](config)
        config["version"] = version
    return config
```

**Migration is automatic and transparent** — when a v1 config is loaded by v2 code, the migration runs on load and re-saves the new format.
