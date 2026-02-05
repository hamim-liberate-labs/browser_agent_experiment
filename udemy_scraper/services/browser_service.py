"""Browser automation service for Udemy scraping."""

import asyncio
import random
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from udemy_scraper.config import get_browser_settings, get_scraper_settings
from udemy_scraper.exceptions import BrowserError, CloudflareBlockedError

# Stealth mode detection
try:
    from playwright_stealth import Stealth
    _stealth_instance = Stealth()
    STEALTH_AVAILABLE = True
except ImportError:
    try:
        from playwright_stealth import stealth_async
        _stealth_instance = None
        STEALTH_AVAILABLE = True
    except ImportError:
        STEALTH_AVAILABLE = False
        _stealth_instance = None


class BrowserService:
    """Manages browser automation for scraping."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._browser_settings = get_browser_settings()
        self._scraper_settings = get_scraper_settings()

    async def start(self) -> BrowserContext:
        """Start browser and create context."""
        if self._browser is not None:
            return self._context

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._browser_settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )
        self._context = await self._browser.new_context(
            viewport={
                "width": self._browser_settings.viewport_width,
                "height": self._browser_settings.viewport_height,
            },
            user_agent=self._browser_settings.user_agent,
        )
        return self._context

    async def close(self):
        """Close browser and release resources."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

        self._context = None
        self._browser = None
        self._playwright = None

    async def new_page(self) -> Page:
        """Create a new page with stealth mode applied."""
        if self._context is None:
            await self.start()

        page = await self._context.new_page()
        await self._apply_stealth(page)
        return page

    async def _apply_stealth(self, page: Page):
        """Apply stealth mode to page if available."""
        if not STEALTH_AVAILABLE:
            return

        try:
            if _stealth_instance:
                await _stealth_instance.apply_stealth_async(page)
            else:
                await stealth_async(page)
        except Exception:
            pass

    async def wait_cloudflare(self, page: Page, max_wait: Optional[int] = None) -> bool:
        """Wait for Cloudflare challenge to resolve.

        Args:
            page: Playwright page
            max_wait: Maximum wait time in seconds

        Returns:
            True if challenge resolved, False if timeout
        """
        import time

        max_wait = max_wait or self._scraper_settings.cloudflare_wait
        start = time.time()

        while time.time() - start < max_wait:
            title = await page.title()
            if "just a moment" not in title.lower() and "checking" not in title.lower():
                return True
            await asyncio.sleep(2)

        return False

    async def delay(self, min_s: Optional[float] = None, max_s: Optional[float] = None):
        """Add random delay between actions."""
        min_s = min_s or self._scraper_settings.min_delay
        max_s = max_s or self._scraper_settings.max_delay
        await asyncio.sleep(random.uniform(min_s, max_s))

    async def scroll_page(
        self,
        page: Page,
        iterations: Optional[int] = None,
        scroll_amount: Optional[int] = None
    ):
        """Scroll page to load lazy-loaded content."""
        iterations = iterations or self._scraper_settings.scroll_iterations
        scroll_amount = scroll_amount or self._scraper_settings.scroll_amount

        for _ in range(iterations):
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
            await asyncio.sleep(0.8)

        # Scroll to bottom then back up slightly
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1.5)
        await page.evaluate("window.scrollBy(0, -300)")
        await asyncio.sleep(0.5)

    async def navigate(self, page: Page, url: str, wait_until: str = "domcontentloaded"):
        """Navigate to URL with timeout handling."""
        try:
            await page.goto(
                url,
                wait_until=wait_until,
                timeout=self._browser_settings.timeout
            )
        except Exception as e:
            raise BrowserError(f"Navigation failed: {e}")

    async def scroll_to_pagination(self, page: Page):
        """Scroll pagination element into view."""
        await page.evaluate("""
            () => {
                const pagination = document.querySelector('[class*="pagination"]') ||
                                  document.querySelector('nav[aria-label*="pagination" i]');
                if (pagination) {
                    pagination.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
            }
        """)
        await asyncio.sleep(1)

    async def click_page_2(self, page: Page, topic_url: str) -> bool:
        """Navigate to page 2 of results.

        Returns:
            True if navigation successful
        """
        await self.scroll_to_pagination(page)

        # Try clicking page 2 button
        selectors = [
            'button:has-text("2")',
            'a:has-text("2")',
            '[data-purpose="pagination"] button:has-text("2")',
            'a[aria-label="Go to page 2"]',
            'a[aria-label="Next page"]',
        ]

        for selector in selectors:
            try:
                btn = page.locator(selector).first
                if await btn.is_visible(timeout=2000):
                    await btn.click()
                    await asyncio.sleep(2.5)
                    return True
            except Exception:
                continue

        # Fallback: URL-based pagination
        try:
            separator = "&" if "?" in topic_url else "?"
            page2_url = f"{topic_url}{separator}p=2"
            await page.goto(page2_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(2)
            return True
        except Exception:
            return False
