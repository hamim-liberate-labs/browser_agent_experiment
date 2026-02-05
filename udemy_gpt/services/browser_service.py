"""Browser service for fetching live course details from Udemy.

This module provides Playwright-based browser automation with
stealth mode and Cloudflare handling.
"""

import asyncio
import logging
import random
from typing import Optional

from langsmith import traceable
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from udemy_gpt.config import settings
from udemy_gpt.models import CourseDetails
from udemy_gpt.exceptions import BrowserError

logger = logging.getLogger(__name__)

# Browser instance globals
_browser: Optional[Browser] = None
_playwright = None
_context: Optional[BrowserContext] = None

# Stealth mode setup
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


async def get_browser_context() -> BrowserContext:
    """Get or create browser context.

    Returns:
        Playwright browser context
    """
    global _browser, _playwright, _context

    if _browser is None:
        browser_settings = settings.browser
        _playwright = await async_playwright().start()
        _browser = await _playwright.chromium.launch(
            headless=browser_settings.headless,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        _context = await _browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=browser_settings.user_agent,
        )
        logger.info("Browser context created")

    return _context


async def close_browser() -> None:
    """Close browser resources."""
    global _browser, _playwright, _context

    if _context:
        await _context.close()
    if _browser:
        await _browser.close()
    if _playwright:
        await _playwright.stop()

    _browser = None
    _playwright = None
    _context = None
    logger.info("Browser closed")


async def _wait_for_cloudflare(page: Page, max_wait: Optional[int] = None) -> bool:
    """Wait for Cloudflare challenge to complete.

    Args:
        page: Playwright page
        max_wait: Maximum wait time in seconds

    Returns:
        True if challenge passed, False if timeout
    """
    import time

    max_wait = max_wait or settings.browser.cloudflare_wait
    start = time.time()

    while time.time() - start < max_wait:
        title = await page.title()
        if "just a moment" not in title.lower() and "checking" not in title.lower():
            return True
        await asyncio.sleep(2)

    return False


async def _apply_stealth(page: Page) -> None:
    """Apply stealth mode to page if available."""
    if not STEALTH_AVAILABLE:
        return

    try:
        if _stealth_instance:
            await _stealth_instance.apply_stealth_async(page)
        else:
            from playwright_stealth import stealth_async
            await stealth_async(page)
    except Exception as e:
        logger.debug(f"Stealth application failed: {e}")


@traceable(name="extract_course_details", run_type="tool")
async def _extract_course_details(page: Page) -> dict:
    """Extract detailed course information from page.

    Args:
        page: Playwright page on course detail page

    Returns:
        Dictionary with course details
    """
    return await page.evaluate("""
        () => {
            const getText = (selector) => {
                const el = document.querySelector(selector);
                return el ? el.textContent.trim() : '';
            };

            const getAll = (selector) => {
                return Array.from(document.querySelectorAll(selector))
                    .map(el => el.textContent.trim())
                    .filter(t => t);
            };

            // Basic info
            const title = getText('h1[data-purpose="lead-title"]') ||
                         getText('h1.clp-lead__title') || getText('h1');
            const subtitle = getText('[data-purpose="lead-headline"]') ||
                            getText('.clp-lead__headline');

            // Rating and reviews
            const rating = getText('[data-purpose="rating-number"]');
            const reviewsCount = getText('[data-purpose="reviews"]');
            const students = getText('[data-purpose="enrollment"]');

            // Meta info
            const lastUpdated = getText('[data-purpose="last-update-date"]');
            const language = getText('[data-purpose="lead-course-locale"]');
            const level = getText('[data-purpose="course-level"]');

            // Pricing
            const price = getText('[data-purpose="course-price-text"] span span');
            const originalPrice = getText('[data-purpose="original-price-text"] span span');

            // Content stats
            const duration = getText('[data-purpose="video-duration"]');
            const lectureCount = getText('[data-purpose="lecture-count"]');
            const sectionCount = getText('[data-purpose="section-count"]');

            // What you'll learn
            const objectives = getAll('[data-purpose="objective-list"] li span');

            // Requirements
            const requirements = getAll('[data-purpose="prerequisites-list"] li');

            // Target audience
            const targetAudience = getAll('[data-purpose="target-audience-list"] li');

            // Curriculum
            const curriculum = [];
            const sections = document.querySelectorAll('[data-purpose="course-curriculum"] > div');
            sections.forEach((section, idx) => {
                const sectionTitle = section.querySelector('[class*="section-title"]')?.textContent?.trim();
                if (sectionTitle && idx < 10) {
                    curriculum.push({ section: sectionTitle, index: idx + 1 });
                }
            });

            // Instructor
            const instructorName = getText('[data-purpose="instructor-name-top"]');
            const instructorTitle = getText('[data-purpose="instructor-title"]');

            // Reviews
            const reviews = [];
            const reviewEls = document.querySelectorAll('[data-purpose="review-comment-content"]');
            reviewEls.forEach((el, idx) => {
                if (idx < 5) {
                    reviews.push({ content: el.textContent?.trim()?.slice(0, 300) || '' });
                }
            });

            return {
                title, subtitle, rating, reviews_count: reviewsCount, students,
                last_updated: lastUpdated, language, level, price, original_price: originalPrice,
                duration, lectures: lectureCount, sections: sectionCount,
                objectives, requirements, target_audience: targetAudience,
                curriculum, instructor_name: instructorName, instructor_title: instructorTitle, reviews
            };
        }
    """)


async def _click_expand_buttons(page: Page) -> int:
    """Click expand/show more buttons to reveal full content.

    Args:
        page: Playwright page

    Returns:
        Number of buttons clicked
    """
    clicked = 0
    expand_selectors = [
        'button[data-purpose="expand-toggle"]',
        'button:has-text("Expand all sections")',
        'button:has-text("Show more")',
        '[data-purpose="show-more"]',
        'button:has-text("See more")',
    ]

    for selector in expand_selectors:
        try:
            buttons = page.locator(selector)
            count = await buttons.count()
            for i in range(min(count, 5)):  # Max 5 clicks per selector
                try:
                    btn = buttons.nth(i)
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        clicked += 1
                        await asyncio.sleep(0.3)
                except Exception:
                    pass
        except Exception:
            pass

    if clicked > 0:
        logger.info(f"Clicked {clicked} expand buttons")

    return clicked


@traceable(name="fetch_course_details", run_type="chain")
async def fetch_course_details(course_url: str) -> Optional[CourseDetails]:
    """Fetch detailed course information from Udemy URL.

    Args:
        course_url: Full Udemy course URL

    Returns:
        CourseDetails object or None if fetch fails
    """
    if not course_url:
        return None

    ctx = await get_browser_context()
    page = await ctx.new_page()

    try:
        await _apply_stealth(page)

        # Navigate to course page
        logger.info(f"Navigating to: {course_url}")
        await page.goto(
            course_url,
            wait_until="domcontentloaded",
            timeout=settings.browser.timeout
        )
        await asyncio.sleep(random.uniform(2, 3))

        # Wait for Cloudflare
        if not await _wait_for_cloudflare(page):
            logger.warning("Cloudflare challenge not resolved")
            return None

        # Scroll to load dynamic content
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(0.5)

        # Click expand buttons to reveal full content
        await _click_expand_buttons(page)

        # Final scroll and wait
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        # Extract details
        data = await _extract_course_details(page)

        return CourseDetails(
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            url=course_url,
            rating=data.get("rating", ""),
            reviews_count=data.get("reviews_count", ""),
            students=data.get("students", ""),
            last_updated=data.get("last_updated", ""),
            language=data.get("language", ""),
            level=data.get("level", ""),
            price=data.get("price", ""),
            original_price=data.get("original_price", ""),
            duration=data.get("duration", ""),
            lectures=data.get("lectures", ""),
            sections=data.get("sections", ""),
            objectives=data.get("objectives", []),
            requirements=data.get("requirements", []),
            target_audience=data.get("target_audience", []),
            curriculum=data.get("curriculum", []),
            instructor_name=data.get("instructor_name", ""),
            instructor_title=data.get("instructor_title", ""),
            reviews=data.get("reviews", []),
        )

    except Exception as e:
        logger.error(f"Browser error fetching course details: {e}")
        return None

    finally:
        await page.close()
