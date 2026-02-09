"""Playwright browser lifecycle manager."""

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
        slowmo_ms: int = 0,
        locale: str = "en-US",
        timezone_id: str = "America/Los_Angeles",
        user_agent: str | None = None,
        stealth: bool = True,
    ) -> None:
        """Initialize browser manager.

        Args:
            headless: Run browser without visible window
            timeout: Default timeout for page operations in ms
        """
        self.headless = headless
        self.timeout = timeout
        self.slowmo_ms = slowmo_ms
        self.locale = locale
        self.timezone_id = timezone_id
        self.user_agent = user_agent
        self.stealth = stealth
        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None

    async def launch(self) -> "BrowserManager":
        """Launch browser and create context.

        Returns:
            self for fluent API
        """
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slowmo_ms,
            args=[
                "--disable-extensions",
                "--disable-sync",
                "--no-first-run",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        context_kwargs = {
            "viewport": self.DEFAULT_VIEWPORT,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "extra_http_headers": {
                "Accept-Language": "en-US,en;q=0.9",
            },
            "ignore_https_errors": False,
            "java_script_enabled": True,
        }
        if self.user_agent:
            context_kwargs["user_agent"] = self.user_agent

        self._context = await self._browser.new_context(**context_kwargs)

        self._context.set_default_timeout(self.timeout)

        if self.stealth:
            await self._context.add_init_script(_stealth_init_script())

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
    def context(self) -> BrowserContext | None:
        """Get the browser context."""
        return self._context

    @property
    def browser(self) -> Browser | None:
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


def _stealth_init_script() -> str:
    return """
// Minimal stealth patches to reduce obvious automation signals.
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = window.chrome || { runtime: {} };
"""
