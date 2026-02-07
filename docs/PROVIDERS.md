# faaadmv Provider Design

## Overview

Providers encapsulate all state-specific DMV portal logic. Each provider knows how to:
- Navigate its state's DMV website
- Fill forms with user data
- Parse responses and errors
- Handle state-specific requirements

## Provider Interface

```python
from abc import ABC, abstractmethod
from typing import Optional
from playwright.async_api import Page, BrowserContext

from faaadmv.models import (
    UserConfig,
    RegistrationStatus,
    EligibilityResult,
    FeeBreakdown,
    RenewalResult,
)


class BaseProvider(ABC):
    """Abstract base class for DMV providers."""

    # Class attributes - override in subclasses
    state_code: str
    state_name: str
    portal_base_url: str
    allowed_domains: list[str]

    def __init__(self, context: BrowserContext):
        self.context = context
        self.page: Optional[Page] = None

    async def initialize(self) -> None:
        """Create new page and set up interceptors."""
        self.page = await self.context.new_page()
        await self._setup_request_interception()

    async def cleanup(self) -> None:
        """Close page and release resources."""
        if self.page:
            await self.page.close()
            self.page = None

    async def _setup_request_interception(self) -> None:
        """Block analytics and tracking requests."""
        await self.page.route("**/*google-analytics*", lambda r: r.abort())
        await self.page.route("**/*facebook*", lambda r: r.abort())

    # ─────────────────────────────────────────────────────────────
    # Abstract methods - must be implemented by each state provider
    # ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def get_registration_status(
        self,
        plate: str,
        vin_last5: str,
    ) -> RegistrationStatus:
        """
        Check current registration status.

        Args:
            plate: License plate number
            vin_last5: Last 5 characters of VIN

        Returns:
            RegistrationStatus with expiration and status

        Raises:
            NavigationError: If portal is unreachable
            VehicleNotFoundError: If plate/VIN combo not found
        """
        ...

    @abstractmethod
    async def validate_eligibility(
        self,
        plate: str,
        vin_last5: str,
    ) -> EligibilityResult:
        """
        Check if vehicle is eligible for online renewal.

        Returns:
            EligibilityResult with smog/insurance status

        Raises:
            SmogCheckError: If smog certification missing/failed
            InsuranceError: If insurance not verified
        """
        ...

    @abstractmethod
    async def get_fee_breakdown(self) -> FeeBreakdown:
        """
        Get itemized registration fees.

        Must be called after validate_eligibility().

        Returns:
            FeeBreakdown with itemized fees and total
        """
        ...

    @abstractmethod
    async def submit_renewal(
        self,
        config: UserConfig,
    ) -> RenewalResult:
        """
        Complete the renewal with payment.

        Args:
            config: Full user configuration including payment

        Returns:
            RenewalResult with confirmation number and receipt path

        Raises:
            PaymentError: If payment is declined
            DMVError: If submission fails
        """
        ...

    @abstractmethod
    def get_selectors(self) -> dict[str, str]:
        """
        Return CSS/XPath selectors for portal elements.

        Returns:
            Dict mapping element names to selectors
        """
        ...

    # ─────────────────────────────────────────────────────────────
    # Helper methods - available to all providers
    # ─────────────────────────────────────────────────────────────

    async def wait_for_navigation(self, timeout: int = 30000) -> None:
        """Wait for page navigation to complete."""
        await self.page.wait_for_load_state("networkidle", timeout=timeout)

    async def fill_field(self, selector: str, value: str) -> None:
        """Fill a form field with retry logic."""
        await self.page.wait_for_selector(selector, state="visible")
        await self.page.fill(selector, value)

    async def click_and_wait(self, selector: str) -> None:
        """Click element and wait for navigation."""
        await self.page.click(selector)
        await self.wait_for_navigation()

    async def has_captcha(self) -> bool:
        """Detect if CAPTCHA is present on page."""
        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            "#captcha",
        ]
        for selector in captcha_selectors:
            if await self.page.query_selector(selector):
                return True
        return False

    async def screenshot(self, path: str) -> None:
        """Take screenshot for debugging."""
        await self.page.screenshot(path=path, full_page=True)

    async def save_pdf(self, path: str) -> None:
        """Save current page as PDF."""
        await self.page.pdf(path=path, format="Letter")
```

## California DMV Provider

```python
from datetime import datetime, date
from decimal import Decimal
import re

from faaadmv.providers.base import BaseProvider
from faaadmv.models import (
    RegistrationStatus,
    StatusType,
    EligibilityResult,
    SmogStatus,
    InsuranceStatus,
    FeeBreakdown,
    FeeItem,
    RenewalResult,
)
from faaadmv.exceptions import (
    VehicleNotFoundError,
    SmogCheckError,
    InsuranceError,
    PaymentError,
)


class CADMVProvider(BaseProvider):
    """California DMV provider implementation."""

    state_code = "CA"
    state_name = "California"
    portal_base_url = "https://www.dmv.ca.gov"
    allowed_domains = ["dmv.ca.gov", "www.dmv.ca.gov"]

    # Portal URLs
    STATUS_URL = "https://www.dmv.ca.gov/wasapp/ipp2/initPers.do"
    RENEW_URL = "https://www.dmv.ca.gov/wasapp/vr/vr.do"

    def get_selectors(self) -> dict[str, str]:
        """CA DMV portal selectors."""
        return {
            # Status page
            "plate_input": "#licPlate",
            "vin_input": "#lastFiveVin",
            "submit_button": "input[type='submit'][value='Submit']",

            # Results page
            "vehicle_info": ".vehicle-info",
            "expiration_date": ".expiration-date",
            "status_text": ".registration-status",

            # Renewal page
            "owner_name": "#ownerName",
            "owner_phone": "#phone",
            "owner_email": "#email",
            "street_address": "#street",
            "city": "#city",
            "state": "#state",
            "zip": "#zip",

            # Payment page
            "card_number": "#cardNumber",
            "card_expiry_month": "#expMonth",
            "card_expiry_year": "#expYear",
            "card_cvv": "#cvv",
            "billing_zip": "#billingZip",
            "pay_button": "#submitPayment",

            # Fee display
            "fee_table": ".fee-breakdown table",
            "total_amount": ".total-amount",

            # Errors
            "error_message": ".error-message, .alert-danger",
            "smog_error": ".smog-error",
            "insurance_error": ".insurance-error",

            # Confirmation
            "confirmation_number": ".confirmation-number",
            "print_receipt": "#printReceipt",
        }

    async def get_registration_status(
        self,
        plate: str,
        vin_last5: str,
    ) -> RegistrationStatus:
        """Check registration status via CA DMV portal."""
        selectors = self.get_selectors()

        # Navigate to status page
        await self.page.goto(self.STATUS_URL)
        await self.wait_for_navigation()

        # Check for CAPTCHA
        if await self.has_captcha():
            raise CaptchaDetectedError("CAPTCHA detected on status page")

        # Fill form
        await self.fill_field(selectors["plate_input"], plate)
        await self.fill_field(selectors["vin_input"], vin_last5)

        # Submit
        await self.click_and_wait(selectors["submit_button"])

        # Check for errors
        error_el = await self.page.query_selector(selectors["error_message"])
        if error_el:
            error_text = await error_el.inner_text()
            if "not found" in error_text.lower():
                raise VehicleNotFoundError(f"Vehicle {plate} not found")
            raise DMVError(error_text)

        # Parse results
        vehicle_info = await self._get_text(selectors["vehicle_info"])
        exp_text = await self._get_text(selectors["expiration_date"])
        status_text = await self._get_text(selectors["status_text"])

        # Parse expiration date
        exp_date = self._parse_date(exp_text)
        days_left = (exp_date - date.today()).days

        # Determine status
        status = self._determine_status(status_text, days_left)

        return RegistrationStatus(
            plate=plate,
            vin_last5=vin_last5,
            vehicle_description=vehicle_info,
            expiration_date=exp_date,
            status=status,
            days_until_expiry=days_left,
        )

    async def validate_eligibility(
        self,
        plate: str,
        vin_last5: str,
    ) -> EligibilityResult:
        """Validate smog and insurance for renewal."""
        selectors = self.get_selectors()

        # Navigate to renewal portal
        await self.page.goto(self.RENEW_URL)
        await self.wait_for_navigation()

        # Fill vehicle info
        await self.fill_field(selectors["plate_input"], plate)
        await self.fill_field(selectors["vin_input"], vin_last5)
        await self.click_and_wait(selectors["submit_button"])

        # Check smog status
        smog_error = await self.page.query_selector(selectors["smog_error"])
        if smog_error:
            error_text = await smog_error.inner_text()
            raise SmogCheckError(error_text)

        smog_status = SmogStatus(
            passed=True,
            check_date=date.today(),  # Actual date would be parsed from page
        )

        # Check insurance status
        insurance_error = await self.page.query_selector(selectors["insurance_error"])
        if insurance_error:
            error_text = await insurance_error.inner_text()
            raise InsuranceError(error_text)

        insurance_status = InsuranceStatus(
            verified=True,
            provider=await self._extract_insurance_provider(),
        )

        return EligibilityResult(
            eligible=True,
            smog=smog_status,
            insurance=insurance_status,
        )

    async def get_fee_breakdown(self) -> FeeBreakdown:
        """Parse fee table from current page."""
        selectors = self.get_selectors()

        fee_table = await self.page.query_selector(selectors["fee_table"])
        if not fee_table:
            raise DMVError("Fee breakdown not found")

        rows = await fee_table.query_selector_all("tr")
        items = []

        for row in rows:
            cells = await row.query_selector_all("td")
            if len(cells) >= 2:
                desc = await cells[0].inner_text()
                amount_text = await cells[1].inner_text()
                amount = self._parse_amount(amount_text)
                if amount > 0:
                    items.append(FeeItem(description=desc.strip(), amount=amount))

        return FeeBreakdown(items=items)

    async def submit_renewal(self, config: UserConfig) -> RenewalResult:
        """Submit renewal with payment."""
        selectors = self.get_selectors()
        payment = config.payment

        # Fill owner info
        await self.fill_field(selectors["owner_name"], config.owner.full_name)
        await self.fill_field(selectors["owner_phone"], config.owner.phone)
        await self.fill_field(selectors["owner_email"], config.owner.email)
        await self.fill_field(selectors["street_address"], config.owner.address.street)
        await self.fill_field(selectors["city"], config.owner.address.city)
        await self.fill_field(selectors["zip"], config.owner.address.zip_code)

        # Fill payment info
        await self.fill_field(
            selectors["card_number"],
            payment.card_number.get_secret_value()
        )
        await self.page.select_option(
            selectors["card_expiry_month"],
            str(payment.expiry_month)
        )
        await self.page.select_option(
            selectors["card_expiry_year"],
            str(payment.expiry_year)
        )
        await self.fill_field(
            selectors["card_cvv"],
            payment.cvv.get_secret_value()
        )
        await self.fill_field(selectors["billing_zip"], payment.billing_zip)

        # Submit payment
        await self.click_and_wait(selectors["pay_button"])

        # Check for payment error
        error_el = await self.page.query_selector(selectors["error_message"])
        if error_el:
            error_text = await error_el.inner_text()
            if "declined" in error_text.lower():
                raise PaymentError("Payment declined")
            raise PaymentError(error_text)

        # Extract confirmation
        conf_el = await self.page.query_selector(selectors["confirmation_number"])
        confirmation = await conf_el.inner_text() if conf_el else None

        # Save receipt PDF
        receipt_path = f"./dmv_receipt_{date.today().isoformat()}.pdf"
        await self.save_pdf(receipt_path)

        # Parse new expiration (typically 1 year from now)
        new_exp = date(date.today().year + 1, date.today().month, 1)

        return RenewalResult(
            success=True,
            confirmation_number=confirmation,
            new_expiration_date=new_exp,
            amount_paid=await self._get_total_paid(),
            receipt_path=receipt_path,
        )

    # ─────────────────────────────────────────────────────────────
    # Private helper methods
    # ─────────────────────────────────────────────────────────────

    async def _get_text(self, selector: str) -> str:
        """Get inner text of element."""
        el = await self.page.query_selector(selector)
        return await el.inner_text() if el else ""

    def _parse_date(self, text: str) -> date:
        """Parse date from various formats."""
        # Try common formats
        for fmt in ("%m/%d/%Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Cannot parse date: {text}")

    def _parse_amount(self, text: str) -> Decimal:
        """Parse dollar amount from text."""
        match = re.search(r"\$?([\d,]+\.?\d*)", text)
        if match:
            return Decimal(match.group(1).replace(",", ""))
        return Decimal("0")

    def _determine_status(self, text: str, days_left: int) -> StatusType:
        """Determine status type from text and days."""
        text_lower = text.lower()
        if "expired" in text_lower:
            return StatusType.EXPIRED
        if "pending" in text_lower:
            return StatusType.PENDING
        if "hold" in text_lower:
            return StatusType.HOLD
        if days_left <= 90:
            return StatusType.EXPIRING_SOON
        return StatusType.CURRENT

    async def _extract_insurance_provider(self) -> str:
        """Extract insurance provider name from page."""
        # Implementation depends on actual page structure
        return "Verified"

    async def _get_total_paid(self) -> Decimal:
        """Get total amount from confirmation page."""
        selectors = self.get_selectors()
        total_el = await self.page.query_selector(selectors["total_amount"])
        if total_el:
            text = await total_el.inner_text()
            return self._parse_amount(text)
        return Decimal("0")
```

## Provider Registry

```python
from typing import Type, Optional
from faaadmv.providers.base import BaseProvider
from faaadmv.providers.ca_dmv import CADMVProvider

# Register all available providers
PROVIDERS: dict[str, Type[BaseProvider]] = {
    "CA": CADMVProvider,
    # "TX": TXDMVProvider,  # Future
    # "NY": NYDMVProvider,  # Future
}


def get_provider(state: str) -> Type[BaseProvider]:
    """Get provider class for state."""
    provider = PROVIDERS.get(state.upper())
    if not provider:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"No provider for {state}. Available: {available}")
    return provider


def list_providers() -> list[str]:
    """List available state codes."""
    return list(PROVIDERS.keys())
```

## Adding New Providers

To add support for a new state:

1. Create `faaadmv/providers/{state}_dmv.py`
2. Implement all abstract methods from `BaseProvider`
3. Add selectors for the state's DMV portal
4. Register in `PROVIDERS` dict in `registry.py`
5. Add tests for the new provider

### Template for New Provider

```python
from faaadmv.providers.base import BaseProvider

class XXDMVProvider(BaseProvider):
    """[State Name] DMV provider."""

    state_code = "XX"
    state_name = "[State Name]"
    portal_base_url = "https://..."
    allowed_domains = ["..."]

    def get_selectors(self) -> dict[str, str]:
        return {
            # Map all required selectors
        }

    async def get_registration_status(self, plate, vin_last5):
        # Implement status check
        ...

    async def validate_eligibility(self, plate, vin_last5):
        # Implement eligibility check
        ...

    async def get_fee_breakdown(self):
        # Implement fee parsing
        ...

    async def submit_renewal(self, config):
        # Implement renewal submission
        ...
```
