"""Browser service for fetching live course details from Udemy.

This module provides Playwright-based browser automation with
stealth mode, Cloudflare handling, and LLM-based extraction.
"""

import asyncio
import json
import logging
import random
from typing import Optional

from langsmith import traceable
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from udemy_gpt.config import settings
from udemy_gpt.models import CourseDetails

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

# LLM prompt for course detail extraction
COURSE_DETAIL_SYSTEM_PROMPT = """You are an expert at extracting detailed course information from Udemy course pages.

Extract information matching these EXACT Udemy page sections:

## HEADER SECTION (top of page)
- title: Course title
- subtitle: Course headline/subtitle
- rating: Course rating (e.g., "4.8")
- ratings_count: Number of ratings (e.g., "31K ratings" or "556,000 ratings")
- students: Students enrolled (e.g., "200,000 students")
- created_by: Instructor name(s)
- last_updated: Last update date
- language: Course language
- subtitles: Available subtitles
- price: Current price
- original_price: Original price if discounted

## "What you'll learn" SECTION
- objectives: Array of all learning points listed

## "This course includes" SECTION
- duration: Video hours (e.g., "22 hours on-demand video")
- articles: Articles count (e.g., "14 articles")
- resources: Downloadable resources (e.g., "19 downloadable resources")
- coding_exercises: Coding exercises if any
- certificate: Certificate info

## "Course content" SECTION
- sections_count: Total sections (e.g., "23 sections")
- lectures_count: Total lectures (e.g., "156 lectures")
- total_length: Total duration (e.g., "22h 13m total length")
- curriculum: Array of section objects with title, lectures, duration

## "Requirements" SECTION
- requirements: Array of all prerequisites

## "Description" SECTION
- description: Full course description text

## "Who this course is for" SECTION
- target_audience: Array of target audience items

## "Instructors" SECTION
For each instructor, extract:
- instructor_name: Full name
- instructor_title: Job title/headline
- instructor_rating: Rating (e.g., "4.6 Instructor Rating")
- instructor_reviews: Reviews count (e.g., "1,329,045 Reviews")
- instructor_students: Students count (e.g., "4,460,382 Students")
- instructor_courses: Courses count (e.g., "87 Courses")
- instructor_bio: Full biography text (after clicking Show more)

## "Student feedback" SECTION
- course_rating: Overall rating (e.g., "4.8 course rating")
- rating_breakdown: Object with star percentages {"5_star": "75%", "4_star": "20%", ...}
- reviews: Array of review objects with content, rating, date, reviewer_name

Return as JSON:
{
  "title": "", "subtitle": "", "rating": "", "ratings_count": "", "students": "",
  "created_by": "", "last_updated": "", "language": "", "price": "", "original_price": "",
  "objectives": [], "duration": "", "articles": "", "resources": "", "coding_exercises": "", "certificate": "",
  "sections_count": "", "lectures_count": "", "total_length": "", "curriculum": [],
  "requirements": [], "description": "", "target_audience": [],
  "instructor_name": "", "instructor_title": "", "instructor_rating": "",
  "instructor_reviews": "", "instructor_students": "", "instructor_courses": "", "instructor_bio": "",
  "course_rating": "", "rating_breakdown": {}, "reviews": []
}

Rules:
1. Extract EXACTLY as shown on page - preserve formatting (e.g., "4.8", "31K ratings")
2. Keep numbers with commas/K/M suffixes as-is
3. Use empty string "" for missing fields, empty array [] for missing lists
4. Return ONLY valid JSON, no markdown"""

COURSE_DETAIL_USER_PROMPT = """Extract detailed information from this Udemy course page:

URL: {url}

Page Text:
{page_text}

Return a JSON object with all course details."""


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
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        )
        _context = await _browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=browser_settings.user_agent,
        )
        # Add session cookie
        await _context.add_cookies([{
            "name": "visitor_id",
            "value": str(random.randint(100000, 999999)),
            "domain": ".udemy.com",
            "path": "/"
        }])
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

    cloudflare_indicators = [
        "just a moment", "checking your browser", "please wait",
        "verifying you are human"
    ]

    while time.time() - start < max_wait:
        title = await page.title()
        title_lower = title.lower()

        is_cloudflare = any(ind in title_lower for ind in cloudflare_indicators)

        if not is_cloudflare:
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


async def _extract_page_text(page: Page) -> str:
    """Extract all visible text from page using DOM tree walker.

    Args:
        page: Playwright page

    Returns:
        All visible text content from the page
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


async def _click_expand_buttons(page: Page) -> int:
    """Click expand/show more buttons to reveal full content.

    Args:
        page: Playwright page

    Returns:
        Number of buttons clicked
    """
    clicked = 0

    expand_selectors = [
        'button:has-text("Expand all sections")',
        'button:has-text("Show more")',
        'button:has-text("See more")',
        '[data-purpose="expand-toggle"]',
        '[data-purpose="show-more"]',
    ]

    for selector in expand_selectors:
        try:
            buttons = page.locator(selector)
            count = await buttons.count()
            for i in range(min(count, 10)):
                try:
                    btn = buttons.nth(i)
                    if await btn.is_visible(timeout=1000):
                        await btn.click()
                        clicked += 1
                        await asyncio.sleep(0.5)
                except Exception:
                    pass
        except Exception:
            pass

    if clicked > 0:
        logger.info(f"Clicked {clicked} expand buttons")

    return clicked


@traceable(name="browser_parse_llm_response", run_type="parser")
def _parse_llm_response(response_text: str) -> Optional[dict]:
    """Parse course details from LLM response.

    Args:
        response_text: LLM response text

    Returns:
        Parsed dictionary or None
    """
    try:
        # Try to extract JSON from markdown code block
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "{" in response_text:
            start = response_text.find("{")
            end = response_text.rfind("}") + 1
            json_str = response_text[start:end]
        else:
            return None

        details = json.loads(json_str)
        return details if isinstance(details, dict) else None
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return None


@traceable(name="browser_fetch_course_details", run_type="chain")
async def fetch_course_details(course_url: str) -> Optional[CourseDetails]:
    """Fetch detailed course information from Udemy URL using LLM extraction.

    Args:
        course_url: Full Udemy course URL

    Returns:
        CourseDetails object or None if fetch fails
    """
    if not course_url:
        return None

    # Import LLM service here to avoid circular imports
    from udemy_gpt.services.llm_service import LLMService

    ctx = await get_browser_context()
    page = await ctx.new_page()
    llm = LLMService()

    try:
        await _apply_stealth(page)

        # Navigate to course page
        logger.info(f"Navigating to: {course_url}")
        await page.goto(
            course_url,
            wait_until="domcontentloaded",
            timeout=settings.browser.timeout
        )
        await asyncio.sleep(random.uniform(3, 5))

        # Wait for Cloudflare
        if not await _wait_for_cloudflare(page):
            logger.warning("Cloudflare challenge not resolved")
            return None

        # Scroll to load dynamic content
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(random.uniform(0.5, 0.8))

        # Click expand buttons to reveal all content
        await _click_expand_buttons(page)
        await asyncio.sleep(1)

        # Scroll through the entire page
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(0.3)

        # Click more expand buttons after scrolling
        await _click_expand_buttons(page)
        await asyncio.sleep(0.5)

        # Scroll back to top
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        # Extract all page text
        page_text = await _extract_page_text(page)
        logger.info(f"Extracted {len(page_text)} characters of page text")

        # Limit page text for LLM
        page_text = page_text[:50000]

        # Use LLM to extract structured data
        user_prompt = COURSE_DETAIL_USER_PROMPT.format(
            url=course_url,
            page_text=page_text
        )

        logger.info("Sending page text to LLM for extraction...")
        response = await llm.call(
            COURSE_DETAIL_SYSTEM_PROMPT,
            user_prompt,
            temperature=0.1
        )

        # Parse LLM response
        data = _parse_llm_response(response)
        if not data:
            logger.error("Failed to parse LLM response")
            return None

        logger.info(f"Extracted course: {data.get('title', 'Unknown')[:50]}")

        # Convert to CourseDetails model
        return CourseDetails(
            # Header section
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            url=course_url,
            rating=str(data.get("rating", "")),
            ratings_count=str(data.get("ratings_count", "")),
            students=str(data.get("students", "")),
            created_by=data.get("created_by", ""),
            last_updated=data.get("last_updated", ""),
            language=data.get("language", ""),
            level=data.get("level", ""),
            price=str(data.get("price", "")),
            original_price=str(data.get("original_price", "")),
            # What you'll learn
            objectives=data.get("objectives", []) or [],
            # This course includes
            duration=data.get("duration", ""),
            articles=data.get("articles", ""),
            resources=data.get("resources", ""),
            coding_exercises=data.get("coding_exercises", ""),
            certificate=data.get("certificate", ""),
            # Course content
            sections_count=str(data.get("sections_count", "")),
            lectures_count=str(data.get("lectures_count", "")),
            total_length=data.get("total_length", ""),
            curriculum=data.get("curriculum", []) or [],
            # Requirements
            requirements=data.get("requirements", []) or [],
            # Description
            description=data.get("description", ""),
            # Who this course is for
            target_audience=data.get("target_audience", []) or [],
            # Instructors section
            instructor_name=data.get("instructor_name", ""),
            instructor_title=data.get("instructor_title", ""),
            instructor_rating=str(data.get("instructor_rating", "")),
            instructor_reviews=str(data.get("instructor_reviews", "")),
            instructor_students=str(data.get("instructor_students", "")),
            instructor_courses=str(data.get("instructor_courses", "")),
            instructor_bio=data.get("instructor_bio", ""),
            # Student feedback section
            course_rating=data.get("course_rating", ""),
            rating_breakdown=data.get("rating_breakdown", {}) or {},
            reviews=data.get("reviews", []) or [],
        )

    except Exception as e:
        logger.error(f"Browser error fetching course details: {e}")
        return None

    finally:
        await page.close()
