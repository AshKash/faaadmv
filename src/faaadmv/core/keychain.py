"""OS keychain integration for secure credential storage."""

from typing import Optional

import keyring
from keyring.errors import PasswordDeleteError

from faaadmv.models import PaymentInfo

SERVICE_NAME = "faaadmv"


class PaymentKeychain:
    """Secure storage for payment credentials using OS keychain."""

    # Keychain keys
    KEY_CARD_NUMBER = "card_number"
    KEY_CARD_EXPIRY = "card_expiry"
    KEY_CARD_CVV = "card_cvv"
    KEY_BILLING_ZIP = "billing_zip"

    @classmethod
    def store(cls, payment: PaymentInfo) -> None:
        """Store payment info in OS keychain.

        Args:
            payment: PaymentInfo to store
        """
        keyring.set_password(
            SERVICE_NAME,
            cls.KEY_CARD_NUMBER,
            payment.card_number.get_secret_value(),
        )
        keyring.set_password(
            SERVICE_NAME,
            cls.KEY_CARD_EXPIRY,
            f"{payment.expiry_month:02d}/{payment.expiry_year}",
        )
        keyring.set_password(
            SERVICE_NAME,
            cls.KEY_CARD_CVV,
            payment.cvv.get_secret_value(),
        )
        keyring.set_password(
            SERVICE_NAME,
            cls.KEY_BILLING_ZIP,
            payment.billing_zip,
        )

    @classmethod
    def retrieve(cls) -> Optional[PaymentInfo]:
        """Retrieve payment info from OS keychain.

        Returns:
            PaymentInfo if found, None otherwise
        """
        card_number = keyring.get_password(SERVICE_NAME, cls.KEY_CARD_NUMBER)
        if not card_number:
            return None

        expiry = keyring.get_password(SERVICE_NAME, cls.KEY_CARD_EXPIRY)
        cvv = keyring.get_password(SERVICE_NAME, cls.KEY_CARD_CVV)
        billing_zip = keyring.get_password(SERVICE_NAME, cls.KEY_BILLING_ZIP)

        if not all([expiry, cvv, billing_zip]):
            return None

        # Parse expiry
        try:
            exp_parts = expiry.split("/")
            exp_month = int(exp_parts[0])
            exp_year = int(exp_parts[1])
        except (ValueError, IndexError):
            return None

        return PaymentInfo(
            card_number=card_number,
            expiry_month=exp_month,
            expiry_year=exp_year,
            cvv=cvv,
            billing_zip=billing_zip,
        )

    @classmethod
    def delete(cls) -> None:
        """Remove all payment info from keychain."""
        keys = [
            cls.KEY_CARD_NUMBER,
            cls.KEY_CARD_EXPIRY,
            cls.KEY_CARD_CVV,
            cls.KEY_BILLING_ZIP,
        ]
        for key in keys:
            try:
                keyring.delete_password(SERVICE_NAME, key)
            except PasswordDeleteError:
                pass  # Key doesn't exist

    @classmethod
    def exists(cls) -> bool:
        """Check if payment info exists in keychain."""
        return keyring.get_password(SERVICE_NAME, cls.KEY_CARD_NUMBER) is not None
