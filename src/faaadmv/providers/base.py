"""Abstract base provider for DMV automation."""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from playwright.async_api import BrowserContext, Page

from faaadmv.models import (
    EligibilityResult,
    FeeBreakdown,
    RegistrationStatus,
    RenewalResult,
    UserConfig,
)


class BaseProvider(ABC):
    """Abstract base class for DMV providers.

    Each state implements a provider that knows how to:
    - Navigate the state's DMV website
    - Fill forms with user data
    - Parse responses and errors
    - Handle state-specific requirements
    """

    # Override in subclasses
    state_code: str
    state_name: str
    portal_base_url: str
    allowed_domains: list[str]

    def __init__(self, context: "BrowserContext") -> None:
        """Initialize provider with browser context.

        Args:
            context: Playwright browser context
        """
        self.context = context
        self.page: Optional["Page"] = None

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
        if not self.page:
            return

        # Block common trackers
        patterns = [
            "**/google-analytics.com/**",
            "**/googletagmanager.com/**",
            "**/facebook.com/**",
            "**/doubleclick.net/**",
        ]
        for pattern in patterns:
            await self.page.route(pattern, lambda route: route.abort())

    # ─────────────────────────────────────────────────────────────────────
    # Abstract methods - must be implemented by each state provider
    # ─────────────────────────────────────────────────────────────────────

    @abstractmethod
    async def get_registration_status(
        self,
        plate: str,
        vin_last5: str,
    ) -> RegistrationStatus:
        """Check current registration status.

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
        """Check if vehicle is eligible for online renewal.

        Args:
            plate: License plate number
            vin_last5: Last 5 characters of VIN

        Returns:
            EligibilityResult with smog/insurance status

        Raises:
            SmogCheckError: If smog certification missing/failed
            InsuranceError: If insurance not verified
        """
        ...

    @abstractmethod
    async def get_fee_breakdown(self) -> FeeBreakdown:
        """Get itemized registration fees.

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
        """Complete the renewal with payment.

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
        """Return CSS/XPath selectors for portal elements.

        Returns:
            Dict mapping element names to selectors
        """
        ...

    # ─────────────────────────────────────────────────────────────────────
    # Helper methods - available to all providers
    # ─────────────────────────────────────────────────────────────────────

    async def wait_for_navigation(self, timeout: int = 30000) -> None:
        """Wait for page navigation to complete."""
        if self.page:
            await self.page.wait_for_load_state("networkidle", timeout=timeout)

    async def fill_field(self, selector: str, value: str) -> None:
        """Fill a form field with retry logic."""
        if self.page:
            await self.page.wait_for_selector(selector, state="visible")
            await self.page.fill(selector, value)

    async def click_and_wait(self, selector: str) -> None:
        """Click element and wait for navigation."""
        if self.page:
            await self.page.click(selector)
            await self.wait_for_navigation()

    async def has_captcha(self) -> bool:
        """Detect if CAPTCHA is present on page."""
        if not self.page:
            return False

        captcha_selectors = [
            "iframe[src*='recaptcha']",
            "iframe[src*='hcaptcha']",
            ".g-recaptcha",
            "#captcha",
            "[data-sitekey]",
        ]
        for selector in captcha_selectors:
            if await self.page.query_selector(selector):
                return True
        return False

    async def screenshot(self, path: str) -> None:
        """Take screenshot for debugging."""
        if self.page:
            await self.page.screenshot(path=path, full_page=True)

    async def save_pdf(self, path: str) -> None:
        """Save current page as PDF."""
        if self.page:
            await self.page.pdf(path=path, format="Letter")
