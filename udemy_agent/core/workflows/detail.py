"""Course detail workflow for extracting comprehensive course information."""

import asyncio
import json
import logging
import random
from typing import Any, Dict, Optional

from langgraph.graph import END, StateGraph
from langsmith import traceable

from udemy_agent.models import UdemyBrowserState
from udemy_agent.prompts import COURSE_DETAIL_SYSTEM_PROMPT, COURSE_DETAIL_USER_PROMPT
from udemy_agent.services import get_llm_service
from udemy_agent.services.browser_service import get_browser_service, STEALTH_AVAILABLE

logger = logging.getLogger("udemy_agent.workflow.detail")


@traceable(name="navigate_course_detail", run_type="tool")
async def navigate_and_extract_course_detail(state: UdemyBrowserState) -> dict:
    """Navigate to a course detail page and extract comprehensive information."""
    course_url = state.course_detail_url
    if not course_url:
        return {"status": "error", "error_message": "No course URL provided"}

    logger.info(f"Navigating to course: {course_url}")

    browser = get_browser_service()
    page = None

    try:
        page = await browser.new_page()
        await page.goto(course_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(4000)

        # Check for Cloudflare
        page_title = await page.title()
        if "Just a moment" in page_title:
            await page.wait_for_timeout(10000)

        # Scroll to load content
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, window.innerHeight)")
            await asyncio.sleep(random.uniform(0.5, 0.8))

        # Expand sections
        expand_selectors = [
            'button:has-text("Expand all sections")',
            'button:has-text("Show more")',
        ]
        await browser.click_expand_buttons(page, expand_selectors, max_clicks=10)

        # Final scroll
        await page.evaluate("window.scrollTo(0, 0)")
        await page.wait_for_timeout(1000)

        page_text = await browser.extract_page_text(page)
        current_url = page.url

        await page.close()

        return {
            "current_url": current_url,
            "page_text": page_text[:80000],
            "page_type": "course_detail",
            "status": "continue",
        }

    except Exception as e:
        logger.error(f"Course detail navigation error: {e}", exc_info=True)
        if page:
            try:
                await page.close()
            except Exception:
                pass
        return {"status": "error", "error_message": str(e)}


@traceable(name="process_course_detail", run_type="chain")
async def process_course_detail_node(state: UdemyBrowserState) -> dict:
    """Use LLM to extract detailed course information."""
    logger.info("Processing course detail page...")

    llm = get_llm_service()

    try:
        page_text = state.page_text[:40000]
        user_prompt = COURSE_DETAIL_USER_PROMPT.format(
            url=state.current_url,
            page_text=page_text
        )

        response = await llm.call(COURSE_DETAIL_SYSTEM_PROMPT, user_prompt)
        details = _parse_course_details(response)

        if details:
            details["url"] = state.current_url

        return {"course_details": details, "status": "done"}

    except Exception as e:
        logger.error(f"Course detail processing error: {e}", exc_info=True)
        return {"course_details": None, "status": "error", "error_message": str(e)}


def _parse_course_details(response_text: str) -> Optional[Dict[str, Any]]:
    """Parse course details from LLM response."""
    try:
        if "```json" in response_text:
            start = response_text.find("```json") + 7
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
    except (json.JSONDecodeError, ValueError):
        return None


def build_course_detail_workflow() -> StateGraph:
    """Build the Course Detail extraction workflow."""
    workflow = StateGraph(UdemyBrowserState)
    workflow.add_node("navigate_course_detail", navigate_and_extract_course_detail)
    workflow.add_node("process_course_detail", process_course_detail_node)
    workflow.set_entry_point("navigate_course_detail")
    workflow.add_edge("navigate_course_detail", "process_course_detail")
    workflow.add_edge("process_course_detail", END)
    return workflow
