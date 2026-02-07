"""California DMV provider implementation."""

from datetime import date
from decimal import Decimal

from faaadmv.exceptions import (
    DMVError,
    InsuranceError,
    PaymentDeclinedError,
    SmogCheckError,
    VehicleNotFoundError,
)
from faaadmv.models import (
    EligibilityResult,
    FeeBreakdown,
    FeeItem,
    InsuranceStatus,
    RegistrationStatus,
    RenewalResult,
    SmogStatus,
    StatusType,
    UserConfig,
)
from faaadmv.providers.base import BaseProvider


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
        if not self.page:
            raise DMVError("Browser not initialized")

        selectors = self.get_selectors()

        # Navigate to status page
        await self.page.goto(self.STATUS_URL)
        await self.wait_for_navigation()

        # Check for CAPTCHA
        if await self.has_captcha():
            from faaadmv.exceptions import CaptchaDetectedError

            raise CaptchaDetectedError()

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
                raise VehicleNotFoundError(plate)
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
        if not self.page:
            raise DMVError("Browser not initialized")

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
            check_date=date.today(),
        )

        # Check insurance status
        insurance_error = await self.page.query_selector(selectors["insurance_error"])
        if insurance_error:
            error_text = await insurance_error.inner_text()
            raise InsuranceError(error_text)

        insurance_status = InsuranceStatus(
            verified=True,
            provider="Verified",
        )

        return EligibilityResult(
            eligible=True,
            smog=smog_status,
            insurance=insurance_status,
        )

    async def get_fee_breakdown(self) -> FeeBreakdown:
        """Parse fee table from current page."""
        if not self.page:
            raise DMVError("Browser not initialized")

        selectors = self.get_selectors()

        fee_table = await self.page.query_selector(selectors["fee_table"])
        if not fee_table:
            raise DMVError("Fee breakdown not found")

        rows = await fee_table.query_selector_all("tr")
        items: list[FeeItem] = []

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
        if not self.page:
            raise DMVError("Browser not initialized")

        if not config.payment:
            raise DMVError("Payment information not provided")

        selectors = self.get_selectors()
        payment = config.payment

        # Fill owner info
        await self.fill_field(selectors["owner_name"], config.owner.full_name)
        await self.fill_field(selectors["owner_phone"], config.owner.phone)
        await self.fill_field(selectors["owner_email"], config.owner.email)
        await self.fill_field(
            selectors["street_address"], config.owner.address.street
        )
        await self.fill_field(selectors["city"], config.owner.address.city)
        await self.fill_field(selectors["zip"], config.owner.address.zip_code)

        # Fill payment info
        await self.fill_field(
            selectors["card_number"],
            payment.card_number.get_secret_value(),
        )
        await self.page.select_option(
            selectors["card_expiry_month"],
            str(payment.expiry_month),
        )
        await self.page.select_option(
            selectors["card_expiry_year"],
            str(payment.expiry_year),
        )
        await self.fill_field(
            selectors["card_cvv"],
            payment.cvv.get_secret_value(),
        )
        await self.fill_field(selectors["billing_zip"], payment.billing_zip)

        # Submit payment
        await self.click_and_wait(selectors["pay_button"])

        # Check for payment error
        error_el = await self.page.query_selector(selectors["error_message"])
        if error_el:
            error_text = await error_el.inner_text()
            if "declined" in error_text.lower():
                raise PaymentDeclinedError()
            raise DMVError(error_text)

        # Extract confirmation
        conf_el = await self.page.query_selector(selectors["confirmation_number"])
        confirmation = await conf_el.inner_text() if conf_el else None

        # Save receipt PDF
        receipt_path = f"./dmv_receipt_{date.today().isoformat()}.pdf"
        await self.save_pdf(receipt_path)

        # New expiration (typically 1 year from now)
        new_exp = date(date.today().year + 1, date.today().month, 1)

        return RenewalResult(
            success=True,
            confirmation_number=confirmation,
            new_expiration_date=new_exp,
            receipt_path=receipt_path,
        )

    # ─────────────────────────────────────────────────────────────────────
    # Private helper methods
    # ─────────────────────────────────────────────────────────────────────

    async def _get_text(self, selector: str) -> str:
        """Get inner text of element."""
        if not self.page:
            return ""
        el = await self.page.query_selector(selector)
        return await el.inner_text() if el else ""

    def _parse_date(self, text: str) -> date:
        """Parse date from various formats."""
        from datetime import datetime

        # Try common formats
        for fmt in ("%m/%d/%Y", "%B %d, %Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text.strip(), fmt).date()
            except ValueError:
                continue

        # Default to 1 year from now if parsing fails
        return date(date.today().year + 1, date.today().month, 1)

    def _parse_amount(self, text: str) -> Decimal:
        """Parse dollar amount from text."""
        import re

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
