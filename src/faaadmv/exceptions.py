"""Custom exceptions for faaadmv."""

from typing import Optional


class FaaadmvError(Exception):
    """Base exception for all faaadmv errors."""

    def __init__(self, message: str, details: Optional[str] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(message)


# ─────────────────────────────────────────────────────────────────────────────
# Config Errors
# ─────────────────────────────────────────────────────────────────────────────


class ConfigError(FaaadmvError):
    """Base class for configuration errors."""


class ConfigNotFoundError(ConfigError):
    """Configuration file not found."""

    def __init__(self) -> None:
        super().__init__(
            "Configuration not found",
            "Run 'faaadmv register' to set up your vehicle.",
        )


class ConfigDecryptionError(ConfigError):
    """Failed to decrypt configuration."""

    def __init__(self) -> None:
        super().__init__(
            "Failed to decrypt configuration",
            "Check your passphrase and try again.",
        )


class ConfigValidationError(ConfigError):
    """Configuration validation failed."""

    def __init__(self, field: str, reason: str) -> None:
        super().__init__(
            f"Invalid configuration: {field}",
            reason,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Browser Errors
# ─────────────────────────────────────────────────────────────────────────────


class BrowserError(FaaadmvError):
    """Base class for browser automation errors."""


# ─────────────────────────────────────────────────────────────────────────────
# DMV Errors
# ─────────────────────────────────────────────────────────────────────────────


class DMVError(FaaadmvError):
    """Base class for DMV-specific errors."""


class VehicleNotFoundError(DMVError):
    """Vehicle not found in DMV system."""

    def __init__(self, plate: str) -> None:
        super().__init__(
            f"Vehicle not found: {plate}",
            "Check your license plate and VIN, then try again.",
        )


class EligibilityError(DMVError):
    """Vehicle not eligible for online renewal."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            "Vehicle not eligible for online renewal",
            reason,
        )


class SmogCheckError(DMVError):
    """Smog certification issue."""

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(
            "Smog check required",
            message or "Visit a STAR-certified smog station to complete testing.",
        )


class InsuranceError(DMVError):
    """Insurance verification issue."""

    def __init__(self, message: Optional[str] = None) -> None:
        super().__init__(
            "Insurance not verified",
            message or "Contact your insurance provider to verify coverage with DMV.",
        )


class PaymentError(DMVError):
    """Payment processing error."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            "Payment failed",
            reason,
        )


class PaymentDeclinedError(PaymentError):
    """Payment was declined."""

    def __init__(self) -> None:
        super().__init__("Card declined. Check your card details or try another card.")


# ─────────────────────────────────────────────────────────────────────────────
# CAPTCHA Errors
# ─────────────────────────────────────────────────────────────────────────────


class CaptchaError(FaaadmvError):
    """Base class for CAPTCHA errors."""


class CaptchaDetectedError(CaptchaError):
    """CAPTCHA detected on page."""

    def __init__(self) -> None:
        super().__init__(
            "CAPTCHA detected",
            "Try running with --headed flag to solve manually.",
        )


class CaptchaSolveFailedError(CaptchaError):
    """Failed to solve CAPTCHA."""

    def __init__(self, method: str) -> None:
        super().__init__(
            "Failed to solve CAPTCHA",
            f"Method '{method}' failed. Try --headed flag for manual solving.",
        )
