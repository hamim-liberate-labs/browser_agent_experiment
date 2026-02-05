"""Course details handler.

Handles details intent for showing detailed course information.
"""

import logging
import re

from langsmith import traceable

from udemy_gpt.data import get_index, search_course_by_name, generate_course_url
from udemy_gpt.models import IntentClassification, ConversationState
from udemy_gpt.prompts import get_response_prompt
from udemy_gpt.services import fetch_course_details, LLMService
from udemy_gpt.utils import format_live_details, format_kb_details

logger = logging.getLogger(__name__)


def _extract_course_name(message: str) -> str:
    """Extract course name from user message.

    Args:
        message: User message

    Returns:
        Extracted course name or empty string
    """
    # Common patterns for course name references
    patterns = [
        r"details?\s+(?:of|for|about)\s+(?:the\s+)?(?:course\s+)?['\"]?(.+?)['\"]?\s*$",
        r"(?:tell|show|get)\s+(?:me\s+)?(?:about|details?\s+(?:of|for))\s+(?:the\s+)?(?:course\s+)?['\"]?(.+?)['\"]?\s*$",
        r"(?:the\s+)?course\s+['\"]?(.+?)['\"]?\s*$",
    ]

    message_lower = message.lower().strip()

    for pattern in patterns:
        match = re.search(pattern, message_lower, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Skip if it's just a number
            if not name.isdigit():
                return name

    return ""


class DetailsHandler:
    """Handler for course details intent."""

    def __init__(self, llm_service: LLMService):
        """Initialize details handler.

        Args:
            llm_service: LLM service for generating responses
        """
        self._llm = llm_service

    @traceable(name="handle_details", run_type="chain")
    async def handle_details(
        self,
        intent: IntentClassification,
        user_message: str,
        state: ConversationState,
        conversation_history: str = "",
    ) -> str:
        """Handle course details request.

        Args:
            intent: Classified intent with course reference
            user_message: Original user message
            state: Conversation state with search results
            conversation_history: Optional history

        Returns:
            Detailed course information response
        """
        course = None
        course_url = ""
        course_title = ""

        # Try to get course by number first
        course_idx = intent.course_reference
        if course_idx is None:
            match = re.search(r'\bcourse\s+(\d+)\b', user_message, re.IGNORECASE)
            if match:
                course_idx = int(match.group(1))

        # If we have a valid course number and search results, use them
        if course_idx and state.last_search_results:
            idx = course_idx - 1
            if 0 <= idx < len(state.last_search_results):
                course = state.last_search_results[idx]
                course_url = course.get("url", "")
                course_title = course.get("title", "")
                logger.info(f"Found course by index {course_idx}: {course_title[:60]}")

        # If no course found by number, try to find by name
        if not course:
            course_name = _extract_course_name(user_message)
            if course_name:
                logger.info(f"Searching for course by name: {course_name}")
                index = get_index()
                course = search_course_by_name(
                    course_name,
                    index,
                    state.last_search_results
                )

                if course:
                    course_url = course.get("url", "")
                    course_title = course.get("title", "")
                    logger.info(f"Found course in KB: {course_title[:60]}")
                else:
                    # Generate URL from course name as fallback
                    course_url = generate_course_url(course_name)
                    course_title = course_name
                    logger.info(f"Generated URL for course: {course_url}")

        # If still no course or URL, ask user to search first
        if not course_url:
            return "Please search for courses first, or provide the exact course name."

        # Fetch live details if browser is needed
        details = None
        if intent.needs_browser and course_url:
            logger.info(f"Fetching live details for: {course_title[:80]}")
            logger.info(f"Course URL: {course_url}")
            try:
                details = await fetch_course_details(course_url)
            except Exception as e:
                logger.error(f"Failed to fetch live details: {e}")

        # Format details based on source
        if details and details.title:
            details_text = format_live_details(details)
            source = "Live from Udemy"
        elif course:
            details_text = format_kb_details(course)
            source = "Knowledge Base"
        else:
            return f"Could not fetch details for the course. URL attempted: {course_url}"

        # Build prompt - ask LLM to present extracted data first, then analysis
        prompt = f"""User: {user_message}

Source: {source}

EXTRACTED COURSE DATA:
{details_text}

INSTRUCTIONS:
1. First present the EXACT extracted data in a clean table format
2. Then provide your analysis and insights
3. Do NOT add a separate "Direct Link" at the end - the URL is already in the data"""

        try:
            return await self._llm.call(
                get_response_prompt("details"),
                prompt,
                temperature=0.3,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Details LLM failed: {e}")
            return f"Course details:\n{details_text}"
