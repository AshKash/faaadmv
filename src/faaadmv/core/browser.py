"""Playwright browser lifecycle manager."""

from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright


class BrowserManager:
    """Manages Playwright browser lifecycle.

    Usage:
        async with BrowserManager(headless=True) as bm:
            page = await bm.new_page()
            await page.goto("https://example.com")
    """

    # Default browser settings
    DEFAULT_TIMEOUT = 30000  # 30 seconds
    DEFAULT_VIEWPORT = {"width": 1280, "height": 720}
    DEFAULT_USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )

    # Tracker domains to block
    BLOCKED_PATTERNS = [
        "**/google-analytics.com/**",
        "**/googletagmanager.com/**",
        "**/facebook.com/**",
        "**/doubleclick.net/**",
        "**/facebook.net/**",
        "**/analytics.google.com/**",
    ]

    def __init__(
        self,
        headless: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> None:
        """Initialize browser manager.

        Args:
            headless: Run browser without visible window
            timeout: Default timeout for page operations in ms
        """
        self.headless = headless
        self.timeout = timeout
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None

    async def launch(self) -> "BrowserManager":
        """Launch browser and create context.

        Returns:
            self for fluent API
        """
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            args=[
                "--disable-extensions",
                "--disable-plugins",
                "--disable-sync",
                "--no-first-run",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        self._context = await self._browser.new_context(
            viewport=self.DEFAULT_VIEWPORT,
            user_agent=self.DEFAULT_USER_AGENT,
            ignore_https_errors=False,
            java_script_enabled=True,
        )

        self._context.set_default_timeout(self.timeout)

        # Block analytics/tracking
        for pattern in self.BLOCKED_PATTERNS:
            await self._context.route(pattern, lambda route: route.abort())

        return self

    async def close(self) -> None:
        """Close browser and cleanup resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def new_page(self) -> Page:
        """Create a new page in the browser context.

        Returns:
            New Playwright Page

        Raises:
            RuntimeError: If browser not launched
        """
        if not self._context:
            raise RuntimeError("Browser not launched. Call launch() first.")
        return await self._context.new_page()

    @property
    def context(self) -> Optional[BrowserContext]:
        """Get the browser context."""
        return self._context

    @property
    def browser(self) -> Optional[Browser]:
        """Get the browser instance."""
        return self._browser

    @property
    def is_launched(self) -> bool:
        """Check if browser is running."""
        return self._browser is not None and self._browser.is_connected()

    async def __aenter__(self) -> "BrowserManager":
        """Async context manager entry."""
        return await self.launch()

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit — always cleanup."""
        await self.close()
