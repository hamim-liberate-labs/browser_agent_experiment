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
    message_clean = message.strip()

    # Skip if user is asking by course number (e.g., "course 1", "course 2")
    if re.search(r'\bcourse\s+\d+\b', message_clean, re.IGNORECASE):
        return ""

    # Common patterns for course name references
    patterns = [
        # "get the live details of the XYZ course"
        r"(?:get|fetch|show|tell)\s+(?:me\s+)?(?:the\s+)?(?:live\s+)?details?\s+(?:of|for|about)\s+(?:the\s+)?(.+?)(?:\s+course)?\s*$",
        # "details of XYZ"
        r"details?\s+(?:of|for|about)\s+(?:the\s+)?(.+?)(?:\s+course)?\s*$",
        # "info on the XYZ" / "about the XYZ"
        r"(?:about|info\s+on|information\s+on)\s+(?:the\s+)?(.+?)(?:\s+course)?\s*$",
        # "the XYZ course"
        r"(?:the\s+)?(.+?)\s+course\s*$",
    ]

    for pattern in patterns:
        match = re.search(pattern, message_clean, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Remove trailing "course" if present
            name = re.sub(r'\s+course\s*$', '', name, flags=re.IGNORECASE)
            # Remove leading articles and prepositions
            name = re.sub(r'^(?:the|a|an|on)\s+', '', name, flags=re.IGNORECASE)
            # Skip if it's just a number or too short
            if not re.match(r'^\d+$', name) and len(name) > 3:
                logger.info(f"Extracted course name: '{name}'")
                return name

    # Fallback: If message contains common course keywords, try to extract
    if any(kw in message.lower() for kw in ['details', 'about', 'info', 'fetch', 'get']):
        # Remove common prefixes iteratively
        cleaned = message_clean
        prefix_pattern = r'^(?:get|fetch|show|tell|me|the|live|details?|of|for|about|on|course|info|information)\s+'
        for _ in range(5):  # Max 5 iterations
            new_cleaned = re.sub(prefix_pattern, '', cleaned, flags=re.IGNORECASE)
            if new_cleaned == cleaned:
                break
            cleaned = new_cleaned

        cleaned = re.sub(r'\s+course\s*$', '', cleaned, flags=re.IGNORECASE).strip()

        # Skip if result looks like a number reference
        if re.match(r'^(?:course\s+)?\d+$', cleaned, re.IGNORECASE):
            return ""

        if len(cleaned) > 5:
            logger.info(f"Extracted course name (fallback): '{cleaned}'")
            return cleaned

    return ""


class DetailsHandler:
    """Handler for course details intent."""

    def __init__(self, llm_service: LLMService):
        """Initialize details handler.

        Args:
            llm_service: LLM service for generating responses
        """
        self._llm = llm_service

    @traceable(name="details_handle_request", run_type="chain")
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

        # First, try to extract course name from user message
        course_name = _extract_course_name(user_message)

        # If user mentioned a course name, search for it in CSV first
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
                logger.info(f"Course URL: {course_url}")
            else:
                # Generate URL from course name as fallback
                course_url = generate_course_url(course_name)
                course_title = course_name
                logger.info(f"Generated URL for course: {course_url}")

        # If no course name found, try to get by number
        if not course and not course_url:
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
