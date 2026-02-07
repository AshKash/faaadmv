"""Payment data model."""

from datetime import date

from pydantic import BaseModel, Field, SecretStr, field_validator


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

    @field_validator("cvv")
    @classmethod
    def validate_cvv(cls, v: SecretStr) -> SecretStr:
        """Validate CVV format."""
        cvv = v.get_secret_value()
        if not cvv.isdigit() or len(cvv) not in (3, 4):
            raise ValueError("CVV must be 3 or 4 digits")
        return v

    @staticmethod
    def _luhn_check(card_number: str) -> bool:
        """Validate card number using Luhn algorithm."""
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
        # Card is valid through the end of expiry month
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
