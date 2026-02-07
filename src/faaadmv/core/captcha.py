"""CAPTCHA detection and solving."""

import os
from typing import Optional

from playwright.async_api import Page

from faaadmv.exceptions import CaptchaDetectedError, CaptchaSolveFailedError

# Known CAPTCHA element selectors
CAPTCHA_SELECTORS = [
    "iframe[src*='recaptcha']",
    "iframe[src*='hcaptcha']",
    ".g-recaptcha",
    "#captcha",
    "[data-sitekey]",
    ".h-captcha",
]


class CaptchaSolver:
    """Handles CAPTCHA detection and solving strategies.

    Strategy chain:
    1. Check if CAPTCHA is present
    2. If API key available, attempt automated solve via 2Captcha
    3. If no API key or API fails, fall back to manual solving (headed mode)
    """

    def __init__(self, api_key: Optional[str] = None) -> None:
        """Initialize solver.

        Args:
            api_key: 2Captcha API key. Falls back to CAPTCHA_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("CAPTCHA_API_KEY")

    async def detect(self, page: Page) -> bool:
        """Check if CAPTCHA is present on the page.

        Args:
            page: Playwright page to check

        Returns:
            True if CAPTCHA detected
        """
        for selector in CAPTCHA_SELECTORS:
            element = await page.query_selector(selector)
            if element:
                return True
        return False

    async def solve(self, page: Page, headed: bool = False) -> bool:
        """Attempt to solve CAPTCHA on the page.

        Args:
            page: Playwright page with CAPTCHA
            headed: Whether browser is in headed (visible) mode

        Returns:
            True if CAPTCHA was solved

        Raises:
            CaptchaDetectedError: If CAPTCHA can't be solved (headless, no API key)
            CaptchaSolveFailedError: If solving attempt failed
        """
        if not await self.detect(page):
            return True  # No CAPTCHA present

        # Strategy 1: Try API solve
        if self.api_key:
            solved = await self._solve_via_api(page)
            if solved:
                return True

        # Strategy 2: Manual solve in headed mode
        if headed:
            return await self._solve_manually(page)

        # No solve possible in headless without API key
        raise CaptchaDetectedError()

    async def _solve_via_api(self, page: Page) -> bool:
        """Attempt to solve CAPTCHA via 2Captcha API.

        Args:
            page: Playwright page with CAPTCHA

        Returns:
            True if solved successfully
        """
        # Extract sitekey from page
        sitekey = await self._extract_sitekey(page)
        if not sitekey:
            return False

        try:
            import httpx

            page_url = page.url

            # Submit CAPTCHA to 2Captcha
            async with httpx.AsyncClient(timeout=120) as client:
                # Request solve
                submit_resp = await client.post(
                    "https://2captcha.com/in.php",
                    data={
                        "key": self.api_key,
                        "method": "userrecaptcha",
                        "googlekey": sitekey,
                        "pageurl": page_url,
                        "json": 1,
                    },
                )
                submit_data = submit_resp.json()

                if submit_data.get("status") != 1:
                    return False

                task_id = submit_data["request"]

                # Poll for result (up to 120 seconds)
                import asyncio

                for _ in range(24):  # 24 * 5s = 120s
                    await asyncio.sleep(5)

                    result_resp = await client.get(
                        "https://2captcha.com/res.php",
                        params={
                            "key": self.api_key,
                            "action": "get",
                            "id": task_id,
                            "json": 1,
                        },
                    )
                    result_data = result_resp.json()

                    if result_data.get("status") == 1:
                        token = result_data["request"]
                        # Inject solution into page
                        await page.evaluate(
                            f'document.getElementById("g-recaptcha-response").innerHTML="{token}";'
                        )
                        return True

                    if result_data.get("request") != "CAPCHA_NOT_READY":
                        return False  # Error

        except Exception:
            return False

        return False

    async def _solve_manually(self, page: Page) -> bool:
        """Wait for user to solve CAPTCHA manually in headed mode.

        Args:
            page: Playwright page with visible CAPTCHA

        Returns:
            True if CAPTCHA was solved by user
        """
        import asyncio

        from rich.console import Console

        console = Console()
        console.print()
        console.print(
            "[yellow bold]CAPTCHA detected![/yellow bold] "
            "Please solve it in the browser window."
        )
        console.print("[dim]Waiting up to 120 seconds...[/dim]")

        # Poll until CAPTCHA disappears or timeout
        for i in range(24):  # 24 * 5s = 120s
            await asyncio.sleep(5)

            still_present = await self.detect(page)
            if not still_present:
                console.print("[green]CAPTCHA solved![/green]")
                return True

            remaining = 120 - (i + 1) * 5
            if remaining > 0:
                console.print(f"[dim]  Still waiting... {remaining}s remaining[/dim]")

        raise CaptchaSolveFailedError("manual")

    async def _extract_sitekey(self, page: Page) -> Optional[str]:
        """Extract reCAPTCHA/hCaptcha sitekey from page.

        Args:
            page: Playwright page

        Returns:
            Sitekey string or None
        """
        # Try data-sitekey attribute
        element = await page.query_selector("[data-sitekey]")
        if element:
            return await element.get_attribute("data-sitekey")

        # Try .g-recaptcha
        element = await page.query_selector(".g-recaptcha")
        if element:
            return await element.get_attribute("data-sitekey")

        # Try iframe src parameter
        iframe = await page.query_selector("iframe[src*='recaptcha']")
        if iframe:
            src = await iframe.get_attribute("src")
            if src and "k=" in src:
                # Extract key from URL parameter
                for param in src.split("&"):
                    if param.startswith("k=") or "k=" in param:
                        return param.split("k=")[-1].split("&")[0]

        return None
