"""Tests for exception hierarchy."""

from faaadmv.exceptions import (
    BrowserError,
    CaptchaDetectedError,
    CaptchaSolveFailedError,
    ConfigDecryptionError,
    ConfigError,
    ConfigNotFoundError,
    ConfigValidationError,
    DMVError,
    EligibilityError,
    FaaadmvError,
    InsuranceError,
    NavigationError,
    PaymentDeclinedError,
    PaymentError,
    SelectorNotFoundError,
    SmogCheckError,
    TimeoutError,
    VehicleNotFoundError,
)


class TestExceptionHierarchy:
    def test_base_exception(self):
        e = FaaadmvError("test", "details")
        assert e.message == "test"
        assert e.details == "details"
        assert str(e) == "test"

    def test_config_errors_inherit(self):
        assert issubclass(ConfigError, FaaadmvError)
        assert issubclass(ConfigNotFoundError, ConfigError)
        assert issubclass(ConfigDecryptionError, ConfigError)
        assert issubclass(ConfigValidationError, ConfigError)

    def test_browser_errors_inherit(self):
        assert issubclass(BrowserError, FaaadmvError)
        assert issubclass(NavigationError, BrowserError)
        assert issubclass(TimeoutError, BrowserError)
        assert issubclass(SelectorNotFoundError, BrowserError)

    def test_dmv_errors_inherit(self):
        assert issubclass(DMVError, FaaadmvError)
        assert issubclass(VehicleNotFoundError, DMVError)
        assert issubclass(EligibilityError, DMVError)
        assert issubclass(SmogCheckError, DMVError)
        assert issubclass(InsuranceError, DMVError)
        assert issubclass(PaymentError, DMVError)
        assert issubclass(PaymentDeclinedError, PaymentError)

    def test_captcha_errors_inherit(self):
        assert issubclass(CaptchaDetectedError, FaaadmvError)
        assert issubclass(CaptchaSolveFailedError, FaaadmvError)


class TestExceptionMessages:
    def test_config_not_found(self):
        e = ConfigNotFoundError()
        assert "not found" in e.message.lower()
        assert "faaadmv register" in e.details

    def test_config_decryption(self):
        e = ConfigDecryptionError()
        assert "decrypt" in e.message.lower()
        assert "passphrase" in e.details.lower()

    def test_config_validation(self):
        e = ConfigValidationError("email", "invalid format")
        assert "email" in e.message
        assert "invalid format" in e.details

    def test_vehicle_not_found(self):
        e = VehicleNotFoundError("8ABC123")
        assert "8ABC123" in e.message

    def test_navigation_error(self):
        e = NavigationError("https://dmv.ca.gov", "connection refused")
        assert "dmv.ca.gov" in e.message
        assert "connection refused" in e.details

    def test_timeout_error(self):
        e = TimeoutError("page load", 30)
        assert "page load" in e.message
        assert "30" in e.details

    def test_selector_not_found(self):
        e = SelectorNotFoundError("#plate_input")
        assert "plate_input" in e.details

    def test_captcha_detected(self):
        e = CaptchaDetectedError()
        assert "--headed" in e.details

    def test_captcha_solve_failed(self):
        e = CaptchaSolveFailedError("2captcha")
        assert "2captcha" in e.details

    def test_payment_declined(self):
        e = PaymentDeclinedError()
        assert "declined" in e.message.lower() or "declined" in e.details.lower()

    def test_smog_check_default(self):
        e = SmogCheckError()
        assert "smog" in e.message.lower()
        assert "STAR" in e.details

    def test_smog_check_custom(self):
        e = SmogCheckError("Custom message")
        assert e.details == "Custom message"

    def test_insurance_default(self):
        e = InsuranceError()
        assert "insurance" in e.message.lower()

    def test_insurance_custom(self):
        e = InsuranceError("Policy expired")
        assert e.details == "Policy expired"
