"""Browser automation service for Udemy Agent."""

import asyncio
import logging
import random
import time
from typing import Dict, List, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from udemy_agent.config import get_browser_settings
from udemy_agent.data import BROWSING_PATTERNS, FILTER_SELECTORS
from udemy_agent.exceptions import BrowserError, CloudflareBlockedError, PageLoadError

# Stealth mode detection (v2.0 API with fallback to v1.x)
_stealth_instance = None
stealth_async = None
STEALTH_AVAILABLE = False

try:
    from playwright_stealth import Stealth
    _stealth_instance = Stealth()
    STEALTH_AVAILABLE = True
except ImportError:
    try:
        from playwright_stealth import stealth_async
        STEALTH_AVAILABLE = True
    except ImportError:
        pass

logger = logging.getLogger("udemy_agent.browser")


class BrowserService:
    """Manages browser automation for Udemy browsing."""

    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._settings = get_browser_settings()

    @property
    def stealth_available(self) -> bool:
        """Check if stealth mode is available."""
        return STEALTH_AVAILABLE

    async def start(self) -> BrowserContext:
        """Start browser and create context."""
        if self._browser is not None and self._browser.is_connected():
            return self._context

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._settings.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ]
        )

        self._context = await self._browser.new_context(
            viewport={
                "width": self._settings.viewport_width,
                "height": self._settings.viewport_height,
            },
            user_agent=self._settings.user_agent,
            locale=self._settings.locale,
            timezone_id=self._settings.timezone,
            java_script_enabled=True,
        )

        # Add session cookie
        await self._context.add_cookies([{
            "name": "visitor_id",
            "value": str(random.randint(100000, 999999)),
            "domain": ".udemy.com",
            "path": "/"
        }])

        return self._context

    async def close(self):
        """Close browser and release resources."""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None

    async def get_context(self) -> BrowserContext:
        """Get browser context, starting browser if needed."""
        await self.start()
        return self._context

    async def new_page(self) -> Page:
        """Create a new page with stealth mode applied."""
        context = await self.get_context()
        page = await context.new_page()

        if STEALTH_AVAILABLE:
            try:
                if _stealth_instance:
                    # v2.0 API
                    await _stealth_instance.apply_stealth_async(page)
                elif stealth_async:
                    # v1.x fallback
                    await stealth_async(page)
            except Exception:
                pass

        return page

    async def human_like_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """Add random delay to simulate human behavior."""
        await asyncio.sleep(random.uniform(min_sec, max_sec))

    async def scroll_page_naturally(self, page: Page):
        """Scroll page like a human would."""
        try:
            for _ in range(2):
                await page.evaluate("window.scrollBy(0, window.innerHeight / 2)")
                await asyncio.sleep(random.uniform(0.3, 0.7))
            await page.evaluate("window.scrollTo(0, 0)")
        except Exception:
            pass

    async def handle_cloudflare(self, page: Page, max_wait: Optional[int] = None) -> bool:
        """Handle Cloudflare challenge page.

        Args:
            page: Playwright page
            max_wait: Maximum wait time in seconds

        Returns:
            True if challenge resolved
        """
        max_wait = max_wait or self._settings.cloudflare_max_wait
        start_time = time.time()

        cloudflare_indicators = [
            "Just a moment", "Checking your browser", "Please wait",
            "Verifying you are human", "cf-browser-verification", "challenge-platform"
        ]

        while time.time() - start_time < max_wait:
            page_title = await page.title()
            page_content = await page.content()

            is_cloudflare = any(
                indicator.lower() in page_title.lower() or indicator.lower() in page_content.lower()
                for indicator in cloudflare_indicators
            )

            if not is_cloudflare:
                logger.info("Cloudflare challenge resolved")
                return True

            await asyncio.sleep(2)

        logger.error(f"Cloudflare challenge not resolved within {max_wait}s")
        return False

    async def safe_goto(
        self,
        page: Page,
        url: str,
        timeout: Optional[int] = None,
        retries: int = 3
    ) -> bool:
        """Safely navigate to URL with retry logic and Cloudflare handling.

        Args:
            page: Playwright page
            url: URL to navigate to
            timeout: Navigation timeout
            retries: Number of retry attempts

        Returns:
            True if navigation successful

        Raises:
            PageLoadError: If navigation fails after retries
        """
        timeout = timeout or self._settings.page_timeout

        for attempt in range(1, retries + 1):
            try:
                logger.info(f"Navigating to {url} (attempt {attempt}/{retries})")
                response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)

                if response and response.status >= 400:
                    raise PageLoadError(f"HTTP {response.status} error")

                await page.wait_for_timeout(2000)

                page_title = await page.title()
                if "Just a moment" in page_title or "Checking" in page_title:
                    logger.warning("Cloudflare challenge detected")
                    if await self.handle_cloudflare(page):
                        return True
                    else:
                        raise CloudflareBlockedError("Cloudflare challenge not resolved")

                return True

            except Exception as e:
                if attempt == retries:
                    raise PageLoadError(f"Failed to load {url} after {retries} attempts: {e}")
                logger.warning(f"Navigation attempt {attempt} failed: {e}, retrying...")
                await asyncio.sleep(2 * attempt)

        return False

    async def extract_page_text(self, page: Page) -> str:
        """Extract all visible text from page.

        Args:
            page: Playwright page

        Returns:
            Extracted text content
        """
        return await page.evaluate("""
            () => {
                const walker = document.createTreeWalker(
                    document.body,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: (node) => {
                            const tag = node.parentElement?.tagName?.toLowerCase();
                            if (['script', 'style', 'noscript', 'svg'].includes(tag))
                                return NodeFilter.FILTER_REJECT;
                            return NodeFilter.FILTER_ACCEPT;
                        }
                    }
                );
                const texts = [];
                while (walker.nextNode()) {
                    const t = walker.currentNode.textContent.trim();
                    if (t) texts.push(t);
                }
                return texts.join(' ');
            }
        """)

    async def extract_course_urls(self, page: Page) -> List[Dict[str, str]]:
        """Extract course URLs and titles from a Udemy listing page.

        Args:
            page: Playwright page

        Returns:
            List of {title, url} dictionaries
        """
        return await page.evaluate("""
            () => {
                const courses = [];
                const courseLinks = document.querySelectorAll('a[href*="/course/"]');
                const seen = new Set();
                courseLinks.forEach(link => {
                    const href = link.getAttribute('href');
                    if (!href || seen.has(href)) return;
                    let url = href;
                    if (url.startsWith('/')) {
                        url = 'https://www.udemy.com' + url;
                    }
                    const urlObj = new URL(url);
                    url = urlObj.origin + urlObj.pathname;
                    if (seen.has(url)) return;
                    seen.add(url);
                    let title = '';
                    const titleEl = link.querySelector('h3, h2, [data-purpose="course-title-url"]');
                    if (titleEl) {
                        title = titleEl.textContent.trim();
                    } else {
                        const linkText = link.textContent.trim();
                        if (linkText && linkText.length > 10 && linkText.length < 200) {
                            title = linkText.split('\\n')[0].trim();
                        }
                    }
                    if (url.includes('/course/') && !url.includes('/draft/')) {
                        courses.push({ title, url });
                    }
                });
                return courses;
            }
        """)

    async def apply_filter(self, page: Page, filter_type: str, filter_value: str) -> bool:
        """Apply a specific filter on the Udemy page.

        Args:
            page: Playwright page
            filter_type: Filter type (rating, duration, level, price)
            filter_value: Filter value

        Returns:
            True if filter applied successfully
        """
        logger.info(f"Applying {filter_type} filter: {filter_value}")

        try:
            filter_config = FILTER_SELECTORS.get(f"{filter_type}_filter")
            if not filter_config:
                return False

            trigger_selectors = filter_config.get("trigger", [])
            for trigger_sel in trigger_selectors:
                try:
                    trigger = page.locator(trigger_sel).first
                    if await trigger.is_visible(timeout=2000):
                        await trigger.click()
                        await page.wait_for_timeout(500)

                        option_selectors = filter_config.get("options", {}).get(filter_value, [])
                        for opt_sel in option_selectors:
                            try:
                                option = page.locator(opt_sel).first
                                if await option.is_visible(timeout=1000):
                                    await option.click()
                                    await page.wait_for_timeout(2000)
                                    return True
                            except Exception:
                                continue

                        await page.keyboard.press("Escape")
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.warning(f"Error applying {filter_type} filter: {e}")
            return False

    async def change_sort_option(self, page: Page, target_sort: str) -> bool:
        """Change the sort dropdown on Udemy to the specified option.

        Args:
            page: Playwright page
            target_sort: Sort option name

        Returns:
            True if sort changed successfully
        """
        logger.info(f"Changing sort to: {target_sort}")

        try:
            sort_config = FILTER_SELECTORS.get("sort_dropdown", {})
            trigger_selectors = sort_config.get("trigger", [])

            for selector in trigger_selectors:
                try:
                    dropdown = page.locator(selector).first
                    if await dropdown.is_visible(timeout=2000):
                        await dropdown.click()
                        await page.wait_for_timeout(1000)

                        option_selectors = sort_config.get("options", {}).get(target_sort, [])
                        option_selectors.extend([
                            f'text="{target_sort}"',
                            f'button:has-text("{target_sort}")',
                            f'[role="option"]:has-text("{target_sort}")',
                        ])

                        for opt_selector in option_selectors:
                            try:
                                option = page.locator(opt_selector).first
                                if await option.is_visible(timeout=1000):
                                    await option.click()
                                    await page.wait_for_timeout(3000)
                                    return True
                            except Exception:
                                continue

                        await page.keyboard.press("Escape")
                except Exception:
                    continue

            return False

        except Exception as e:
            logger.warning(f"Error changing sort: {e}")
            return False

    async def load_more_courses(self, page: Page, target_count: int, current_count: int) -> int:
        """Click Show more button to load additional courses.

        Args:
            page: Playwright page
            target_count: Target number of courses
            current_count: Current number of courses

        Returns:
            Estimated new course count
        """
        pagination_config = FILTER_SELECTORS.get("pagination", {})
        load_more_selectors = pagination_config.get("load_more", [])

        clicks = 0
        max_clicks = (target_count - current_count) // 20 + 1

        for _ in range(min(max_clicks, 5)):
            found_button = False
            for selector in load_more_selectors:
                try:
                    button = page.locator(selector).first
                    if await button.is_visible(timeout=2000):
                        await button.click()
                        await page.wait_for_timeout(3000)
                        await page.evaluate("window.scrollBy(0, window.innerHeight)")
                        await page.wait_for_timeout(1000)
                        clicks += 1
                        found_button = True
                        break
                except Exception:
                    continue

            if not found_button:
                break

        return current_count + (clicks * 20)

    async def click_expand_buttons(
        self,
        page: Page,
        selectors: List[str],
        max_clicks: int = 5
    ) -> int:
        """Click expand/show more buttons.

        Args:
            page: Playwright page
            selectors: Button selectors to try
            max_clicks: Maximum buttons to click

        Returns:
            Number of buttons clicked
        """
        clicked = 0

        for selector in selectors:
            if clicked >= max_clicks:
                break

            try:
                buttons = page.locator(selector)
                count = await buttons.count()

                for i in range(min(count, max_clicks - clicked)):
                    try:
                        btn = buttons.nth(i)
                        if await btn.is_visible(timeout=1000):
                            await btn.click()
                            clicked += 1
                            await page.wait_for_timeout(500)
                    except Exception:
                        pass
            except Exception:
                pass

        return clicked


# Global service instance
_browser_service: Optional[BrowserService] = None


def get_browser_service() -> BrowserService:
    """Get the global browser service instance."""
    global _browser_service
    if _browser_service is None:
        _browser_service = BrowserService()
    return _browser_service
