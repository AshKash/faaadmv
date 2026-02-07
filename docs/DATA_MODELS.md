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
```

**Key behavior:**
- Plate length is checked *after* normalization (strips dashes/spaces first)
- VIN rejects I, O, Q characters (per NHTSA standard)
- `masked_vin` shows only last 2 characters

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

    card_number: SecretStr = Field(..., description="Credit/debit card number")
    expiry_month: int = Field(..., ge=1, le=12)
    expiry_year: int = Field(..., ge=2024, le=2099)
    cvv: SecretStr = Field(..., description="3-4 digit security code")
    billing_zip: str = Field(..., pattern=r"^\d{5}$")

    @field_validator("card_number")
    @classmethod
    def validate_card_luhn(cls, v: SecretStr) -> SecretStr:
        """Validate card number format and Luhn checksum."""
        digits = v.get_secret_value().replace(" ", "").replace("-", "")
        if not digits.isdigit():
            raise ValueError("Card number must contain only digits")
        if len(digits) not in (15, 16):
            raise ValueError("Card number must be 15 or 16 digits")
        if digits == "0" * len(digits):
            raise ValueError("Invalid card number")
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
        """Format expiry for display (MM/YY)."""
        return f"{self.expiry_month:02d}/{self.expiry_year % 100:02d}"

    @property
    def card_type(self) -> str:
        """Detect card type from number."""
        first_digit = self.card_number.get_secret_value()[0]
        first_two = self.card_number.get_secret_value()[:2]
        if first_digit == "4":
            return "Visa"
        elif first_two in ("34", "37"):
            return "Amex"
        elif first_digit == "5":
            return "Mastercard"
        elif first_digit == "6":
            return "Discover"
        else:
            return "Card"
```

**Key behavior:**
- Accepts 15-digit (Amex) and 16-digit cards
- Rejects all-zeros card number (BUG-003 fix)
- `SecretStr` prevents accidental logging of card/CVV
- `card_type` detects Visa, Amex, Mastercard, Discover

### UserConfig

**v1 (current):** Single vehicle per config.

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class UserConfig(BaseModel):
    """Complete user configuration (v1 -- single vehicle)."""

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

## Result Models

### StatusType

```python
class StatusType(str, Enum):
    CURRENT = "current"
    EXPIRING_SOON = "expiring_soon"  # Within 90 days
    PENDING = "pending"
    EXPIRED = "expired"
    HOLD = "hold"
```

### RegistrationStatus

```python
class RegistrationStatus(BaseModel):
    """Result of status check."""

    plate: str
    vin_last5: str
    vehicle_description: Optional[str] = None  # e.g., "2019 Honda Accord"
    expiration_date: Optional[date] = None      # None for prose-only DMV response
    status: StatusType
    days_until_expiry: Optional[int] = None     # None when no expiration date
    hold_reason: Optional[str] = None
    status_message: Optional[str] = None        # Raw prose text from DMV
    last_updated: Optional[date] = None         # "as of" date from DMV

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

    @property
    def status_emoji(self) -> str:
        """Return status indicator for display."""
        emoji_map = {
            StatusType.CURRENT: "\u2713",       # checkmark
            StatusType.EXPIRING_SOON: "\u26a0",  # warning
            StatusType.PENDING: "\u26a0",         # warning
            StatusType.EXPIRED: "\u2717",         # X
            StatusType.HOLD: "\u26a0",            # warning
        }
        return emoji_map.get(self.status, "")
```

**Key behavior:**
- `expiration_date` and `days_until_expiry` are `Optional` because the CA DMV status page returns prose text, not structured dates
- `status_message` stores the raw DMV prose (e.g., "An application for Vehicle Registration... is in progress")
- `last_updated` is the "as of" date extracted from a bold `<span>` on the results page

### EligibilityResult

```python
class SmogStatus(BaseModel):
    passed: bool
    check_date: Optional[date] = None
    station: Optional[str] = None
    certificate_number: Optional[str] = None

class InsuranceStatus(BaseModel):
    verified: bool
    provider: Optional[str] = None
    policy_number: Optional[str] = None

class EligibilityResult(BaseModel):
    eligible: bool
    smog: SmogStatus
    insurance: InsuranceStatus
    error_message: Optional[str] = None
```

### FeeBreakdown

```python
class FeeItem(BaseModel):
    description: str
    amount: Decimal

    @property
    def amount_display(self) -> str:
        return f"${self.amount:.2f}"

class FeeBreakdown(BaseModel):
    items: list[FeeItem] = Field(default_factory=list)

    @property
    def total(self) -> Decimal:
        return sum(item.amount for item in self.items)

    @property
    def total_display(self) -> str:
        return f"${self.total:.2f}"
```

### RenewalResult

```python
class RenewalResult(BaseModel):
    success: bool
    confirmation_number: Optional[str] = None
    new_expiration_date: Optional[date] = None
    amount_paid: Optional[Decimal] = None
    receipt_path: Optional[Path] = None
    error_message: Optional[str] = None

    @property
    def amount_display(self) -> str:
        if self.amount_paid:
            return f"${self.amount_paid:.2f}"
        return ""
```

## Serialization

### Config File Format

The config is serialized to TOML before encryption.

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
    2: _migrate_v1_to_v2,      # Single vehicle -> vehicle list (planned)
}
```

Migration is automatic and transparent -- when a v1 config is loaded by v2 code, the migration runs on load and re-saves the new format.
