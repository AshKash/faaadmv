"""California DMV provider implementation."""

import logging
import re
from datetime import date, datetime
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

logger = logging.getLogger(__name__)


class CADMVProvider(BaseProvider):
    """California DMV provider implementation."""

    state_code = "CA"
    state_name = "California"
    portal_base_url = "https://www.dmv.ca.gov"
    allowed_domains = ["dmv.ca.gov", "www.dmv.ca.gov"]

    # Portal URLs (verified against real website 2026-02-07)
    STATUS_URL = "https://www.dmv.ca.gov/wasapp/rsrc/vrapplication.do"
    RENEW_URL = "https://www.dmv.ca.gov/wasapp/vrir/start.do?localeName=en"

    def get_selectors(self) -> dict[str, str]:
        """CA DMV portal selectors (verified against real website)."""
        return {
            # Status check — Step 1: plate
            "status_plate_input": "#licensePlateNumber",
            "status_continue": "button[type='submit']",
            # Status check — Step 2: VIN
            "status_vin_input": "#individualVinHin",
            "status_vin_not_found": "#iVinNotFound",
            # Status check — Results
            "status_results_fieldset": "fieldset",
            "status_results_legend": "legend",
            # Renewal — single page: plate + VIN
            "renew_plate_input": "#plateNumber",
            "renew_vin_input": "#vinLast5",
            "renew_continue": "button[type='submit']",
            # Error selectors
            "error_message": ".error-message, .alert-danger, .text--red",
            "smog_error": ".smog-error",
            "insurance_error": ".insurance-error",
            # Confirmation
            "confirmation_number": ".confirmation-number",
        }

    async def get_registration_status(
        self,
        plate: str,
        vin_last5: str,
    ) -> RegistrationStatus:
        """Check registration status via CA DMV portal.

        Multi-step flow:
        1. Enter license plate → Continue
        2. Enter VIN (last 5) → Continue
        3. Parse results page
        """
        if not self.page:
            raise DMVError("Browser not initialized")

        selectors = self.get_selectors()

        # Step 1: Navigate to status page and enter plate
        logger.info("Status check: navigating to %s", self.STATUS_URL)
        await self.page.goto(self.STATUS_URL)
        await self.page.wait_for_load_state("domcontentloaded")
        logger.debug("Step 1: page loaded, title=%s url=%s", await self.page.title(), self.page.url)

        # Log lightweight fingerprint for debugging bot detection
        fingerprint = await self.collect_fingerprint()
        if fingerprint:
            logger.debug("Status check fingerprint: %s", fingerprint)

        # Check for CAPTCHA on initial page
        if await self.has_captcha():
            from faaadmv.exceptions import CaptchaDetectedError

            logger.warning("CAPTCHA detected on status page")
            raise CaptchaDetectedError()

        await self.fill_field(selectors["status_plate_input"], plate)
        logger.debug("Step 1: filled plate=%s, clicking Continue", plate)

        # Click Continue and wait for step 2 form to appear
        # Use expect_navigation to avoid race condition with networkidle
        async with self.page.expect_navigation(wait_until="domcontentloaded") as nav:
            await self.page.click(selectors["status_continue"])
        response = await nav.value
        if response:
            logger.debug(
                "Step 1 response: status=%s url=%s",
                response.status,
                response.url,
            )

        logger.debug("Step 2: page loaded, title=%s url=%s", await self.page.title(), self.page.url)

        # Step 2: Wait for VIN input to appear and fill it
        await self.page.wait_for_selector(
            selectors["status_vin_input"], state="visible", timeout=15000
        )
        await self.fill_field(selectors["status_vin_input"], vin_last5)
        logger.debug("Step 2: filled vin_last5=%s, clicking Continue", vin_last5)

        # Click Continue and wait for results page
        async with self.page.expect_navigation(wait_until="domcontentloaded") as nav:
            await self.page.click(selectors["status_continue"])
        response = await nav.value
        if response:
            logger.debug(
                "Step 2 response: status=%s url=%s",
                response.status,
                response.url,
            )

        logger.debug("Step 3: results page loaded, url=%s", self.page.url)

        # Check for "VIN/HIN NOT FOUND" error (stays on step 2)
        vin_error = await self.page.query_selector(selectors["status_vin_not_found"])
        if vin_error:
            error_text = await vin_error.inner_text()
            if error_text.strip():
                logger.warning(
                    "VIN not found: %s (url=%s title=%s)",
                    error_text.strip(),
                    self.page.url,
                    await self.page.title(),
                )
                await self._debug_screenshot("vin_not_found")
                raise VehicleNotFoundError(plate)

        # Step 3: Parse results page
        return await self._parse_status_results(plate, vin_last5)

    async def _parse_status_results(
        self, plate: str, vin_last5: str
    ) -> RegistrationStatus:
        """Parse the status results page.

        The results page uses a <fieldset> with <legend>Registration Status Update</legend>
        containing plain <p> tags with prose text. Possible states from HTML comments:
        InProgress, Mailed, ItemsDue, NotYetReceived.
        """
        if not self.page:
            raise DMVError("Browser not initialized")

        # Look for the results fieldset
        fieldset = await self.page.query_selector("fieldset")
        if not fieldset:
            # Take debug screenshot and raise
            await self._debug_screenshot("no_fieldset")
            raise DMVError(
                "Could not parse DMV response",
                "The DMV website may have changed. Try --headed to inspect manually.",
            )

        # Extract all paragraph text from the fieldset
        paragraphs = await fieldset.query_selector_all("p")
        all_text = []
        for p in paragraphs:
            text = await p.inner_text()
            cleaned = text.strip()
            if cleaned:
                all_text.append(cleaned)

        if not all_text:
            await self._debug_screenshot("no_text")
            raise DMVError(
                "No status information found",
                "The DMV website may have changed. Try --headed to inspect manually.",
            )

        full_text = " ".join(all_text)

        # Parse status type from text
        status = self._determine_status_from_text(full_text)

        # Extract "as of" date from the bold span
        last_updated = await self._extract_status_date()

        # Build status message from paragraphs
        status_message = "\n".join(all_text)

        return RegistrationStatus(
            plate=plate,
            vin_last5=vin_last5,
            status=status,
            status_message=status_message,
            last_updated=last_updated,
        )

    async def _extract_status_date(self) -> date | None:
        """Extract the date from the bold styled span on results page."""
        if not self.page:
            return None

        # The date is in a <span> with bold styling
        span = await self.page.query_selector("fieldset span[style*='bold']")
        if span:
            text = await span.inner_text()
            return self._parse_date(text.strip())

        return None

    def _determine_status_from_text(self, text: str) -> StatusType:
        """Determine status type from the prose text on results page.

        Known states from HTML comments: InProgress, Mailed, ItemsDue, NotYetReceived
        """
        text_lower = text.lower()

        if "has been mailed" in text_lower or "was mailed" in text_lower:
            return StatusType.CURRENT
        if "items due" in text_lower or "action is required" in text_lower:
            # "No further action is required" = pending/good
            # "Action is required" without "no further" = items due
            if "no further action" in text_lower:
                return StatusType.PENDING
            return StatusType.HOLD
        if "in progress" in text_lower or "not yet been mailed" in text_lower:
            return StatusType.PENDING
        if "not yet received" in text_lower:
            return StatusType.PENDING
        if "expired" in text_lower:
            return StatusType.EXPIRED

        # Default to pending if we can't determine
        return StatusType.PENDING

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
        await self.fill_field(selectors["renew_plate_input"], plate)
        await self.fill_field(selectors["renew_vin_input"], vin_last5)
        await self.click_and_wait(selectors["renew_continue"])

        # Check for errors
        error_el = await self.page.query_selector(selectors["error_message"])
        if error_el:
            error_text = await error_el.inner_text()
            if "not found" in error_text.lower():
                raise VehicleNotFoundError(plate)

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

        # Try multiple selectors for fee table
        fee_table = None
        for selector in ["table", ".fee-breakdown table", "#feeTable"]:
            fee_table = await self.page.query_selector(selector)
            if fee_table:
                break

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

        payment = config.payment

        # Fill payment info — selectors may need updating once we can test
        # against a real renewal flow (requires eligible vehicle + valid payment)
        await self.fill_field("#cardNumber", payment.card_number.get_secret_value())
        await self.fill_field("#cvv", payment.cvv.get_secret_value())
        await self.fill_field("#billingZip", payment.billing_zip)

        # Submit payment
        await self.click_and_wait("button[type='submit']")

        # Check for payment error
        error_el = await self.page.query_selector(".error-message, .alert-danger")
        if error_el:
            error_text = await error_el.inner_text()
            if "declined" in error_text.lower():
                raise PaymentDeclinedError()
            raise DMVError(error_text)

        # Extract confirmation
        conf_el = await self.page.query_selector(".confirmation-number")
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

    def _parse_date(self, text: str) -> date | None:
        """Parse date from various formats."""
        for fmt in ("%B %d, %Y", "%m/%d/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text.strip(), fmt).date()
            except ValueError:
                continue

        # Try to extract date from within longer text
        match = re.search(
            r"(\w+ \d{1,2}, \d{4}|\d{1,2}/\d{1,2}/\d{4})", text.strip()
        )
        if match:
            for fmt in ("%B %d, %Y", "%m/%d/%Y"):
                try:
                    return datetime.strptime(match.group(1), fmt).date()
                except ValueError:
                    continue

        return None

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

    async def _debug_screenshot(self, label: str) -> None:
        """Save a debug screenshot when parsing fails."""
        if not self.page:
            return
        try:
            path = f"./dmv_debug_{label}_{date.today().isoformat()}.png"
            await self.page.screenshot(path=path, full_page=True)
        except Exception:
            pass  # Don't let screenshot failures mask real errors
