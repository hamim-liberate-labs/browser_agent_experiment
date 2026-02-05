"""Browser workflow for course listing pages."""

import asyncio
import json
import logging
import random
from typing import Any, Dict, List

from langgraph.graph import END, StateGraph
from langsmith import traceable

from udemy_agent.data import BROWSING_PATTERNS, get_action_for_intent
from udemy_agent.models import UdemyBrowserState
from udemy_agent.prompts import PROCESS_TEXT_SYSTEM_PROMPT, PROCESS_TEXT_USER_PROMPT
from udemy_agent.services import get_llm_service
from udemy_agent.services.browser_service import get_browser_service, STEALTH_AVAILABLE

logger = logging.getLogger("udemy_agent.workflow.browser")


@traceable(name="browser_navigate_extract", run_type="tool")
async def navigate_and_extract_node(state: UdemyBrowserState) -> dict:
    """Navigate to URL, apply filters, and extract text."""
    logger.info(f"Task type: {state.task_type}, Query: {state.search_query}")

    browser = get_browser_service()
    filters = state.filters
    page = None

    try:
        page = await browser.new_page()
        delays = BROWSING_PATTERNS["natural_delays"]

        action = get_action_for_intent(state.task_type, state.search_query)
        url = action["url"]
        page_type = action.get("page_type", "unknown")
        sort_by = filters.sort_by if filters and filters.sort_by else action.get("sort_by")
        needs_sort_change = action.get("action") == "change_sort" or (filters and filters.sort_by)

        # Establish session
        if page_type != "homepage":
            await page.goto("https://www.udemy.com/", wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(BROWSING_PATTERNS["session_establishment"]["homepage_wait"])
            await browser.scroll_page_naturally(page)
            await browser.human_like_delay(delays["between_pages"][0], delays["between_pages"][1])

        # Navigate to target
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(action.get("wait_time", 5000))

        # Check for Cloudflare
        page_title = await page.title()
        if "Just a moment" in page_title:
            await page.wait_for_timeout(10000)
            page_title = await page.title()
            if "Just a moment" in page_title:
                await page.close()
                return {"status": "error", "error_message": "Cloudflare protection blocked access"}

        # Check for page not found
        page_content = await page.content()
        not_found_indicators = ["we can't find the page", "page not found", "404"]
        is_not_found = any(indicator in page_content.lower() for indicator in not_found_indicators)

        if is_not_found and state.search_query:
            query_encoded = state.search_query.replace(" ", "+")
            sort_param = ""
            if state.task_type == "top_rated":
                sort_param = "&sort=highest-rated"
            elif state.task_type == "new_courses":
                sort_param = "&sort=newest"
            fallback_url = f"https://www.udemy.com/courses/search/?q={query_encoded}{sort_param}"
            await page.goto(fallback_url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(5000)
            page_type = "search"
            url = fallback_url

        await browser.scroll_page_naturally(page)

        # Apply filters
        if needs_sort_change and sort_by:
            await browser.change_sort_option(page, sort_by)
            await page.wait_for_timeout(3000)

        if filters and filters.min_rating:
            await browser.apply_filter(page, "rating", filters.min_rating)
            await page.wait_for_timeout(2000)

        if filters and filters.duration:
            await browser.apply_filter(page, "duration", filters.duration)
            await page.wait_for_timeout(2000)

        if filters and filters.level and filters.level != "all":
            await browser.apply_filter(page, "level", filters.level)
            await page.wait_for_timeout(2000)

        if filters and filters.price:
            await browser.apply_filter(page, "price", filters.price)
            await page.wait_for_timeout(2000)

        # Pagination
        max_results = filters.max_results if filters else 20
        if max_results > 20:
            await browser.load_more_courses(page, max_results, 20)

        # Final scrolling
        for _ in range(3):
            await browser.scroll_page_naturally(page)
            await browser.human_like_delay(0.5, 1.0)

        await page.evaluate("window.scrollTo(0, 0)")
        current_url = page.url
        page_text = await browser.extract_page_text(page)

        course_urls = []
        if page_type in ["topic", "search", "homepage", "category"]:
            try:
                course_urls = await browser.extract_course_urls(page)
            except Exception:
                pass

        await page.close()

        return {
            "current_url": current_url,
            "page_text": page_text[:50000],
            "status": "continue",
            "page_type": page_type,
            "course_urls": course_urls,
        }

    except Exception as e:
        logger.error(f"Browser error: {e}", exc_info=True)
        if page:
            try:
                await page.close()
            except Exception:
                pass
        return {"status": "error", "error_message": str(e)}


@traceable(name="process_page_text", run_type="chain")
async def process_text_node(state: UdemyBrowserState) -> dict:
    """Use LLM to parse courses from extracted text."""
    logger.info("Processing text with LLM...")

    llm = get_llm_service()

    try:
        page_type = state.page_type
        if not page_type or page_type == "unknown":
            current_url = state.current_url
            if "/topic/" in current_url:
                page_type = "topic"
            elif "/search/" in current_url or "q=" in current_url:
                page_type = "search"
            elif current_url == "https://www.udemy.com/":
                page_type = "homepage"
            else:
                page_type = "unknown"

        page_text = state.page_text[:25000]
        user_prompt = PROCESS_TEXT_USER_PROMPT.format(
            page_type=page_type,
            url=state.current_url,
            page_text=page_text
        )

        response = await llm.call(PROCESS_TEXT_SYSTEM_PROMPT, user_prompt)
        courses = _parse_courses(response)

        # Merge course URLs
        course_urls = state.course_urls or []
        if course_urls and courses:
            for course in courses:
                course_title = course.get("title", "").lower()
                for url_info in course_urls:
                    url_title = url_info.get("title", "").lower()
                    if url_title and course_title:
                        if url_title in course_title or course_title in url_title:
                            course["url"] = url_info["url"]
                            break
                        course_words = set(course_title.split()[:5])
                        url_words = set(url_title.split()[:5])
                        if len(course_words & url_words) >= 2:
                            course["url"] = url_info["url"]
                            break

        logger.info(f"Extracted {len(courses)} courses")
        return {"extracted_courses": courses, "status": "done"}

    except Exception as e:
        logger.error(f"Process text error: {e}", exc_info=True)
        return {"extracted_courses": [], "status": "error", "error_message": str(e)}


def _parse_courses(response_text: str) -> List[Dict[str, Any]]:
    """Parse courses from LLM response."""
    try:
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            json_str = response_text[start:end].strip()
        elif "[" in response_text:
            start = response_text.find("[")
            end = response_text.rfind("]") + 1
            json_str = response_text[start:end]
        else:
            return []

        courses = json.loads(json_str)
        return courses if isinstance(courses, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def build_browser_workflow() -> StateGraph:
    """Build the Browser Agent workflow."""
    workflow = StateGraph(UdemyBrowserState)
    workflow.add_node("navigate_and_extract", navigate_and_extract_node)
    workflow.add_node("process_text", process_text_node)
    workflow.set_entry_point("navigate_and_extract")
    workflow.add_edge("navigate_and_extract", "process_text")
    workflow.add_edge("process_text", END)
    return workflow
