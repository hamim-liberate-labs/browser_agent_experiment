"""Search and recommend handler.

Handles search, recommend, filter, top_valuable, and stats intents.
"""

import logging
from typing import Any, Dict, List, Set

from langsmith import traceable

from udemy_gpt.data import (
    get_index,
    load_multiple_topics,
    validate_topics,
    get_available_topics,
)
from udemy_gpt.models import IntentClassification, ConversationState
from udemy_gpt.prompts import get_analysis_prompt, get_response_prompt
from udemy_gpt.services import filter_courses, get_topic_stats, LLMService
from udemy_gpt.utils import describe_filters, format_courses_for_llm

logger = logging.getLogger(__name__)


class SearchHandler:
    """Handler for search-related intents."""

    def __init__(self, llm_service: LLMService, available_topics: Set[str]):
        """Initialize search handler.

        Args:
            llm_service: LLM service for generating responses
            available_topics: Set of available topic slugs
        """
        self._llm = llm_service
        self._available_topics = available_topics

    @traceable(name="handle_search", run_type="chain")
    async def handle_search(
        self,
        intent: IntentClassification,
        user_message: str,
        state: ConversationState,
        conversation_history: str = "",
    ) -> str:
        """Handle search/recommend intents.

        Args:
            intent: Classified intent with topics and filters
            user_message: Original user message
            state: Conversation state (will be updated)
            conversation_history: Optional conversation history

        Returns:
            Response text with course recommendations
        """
        if not intent.topics:
            suggestions = ", ".join(list(self._available_topics)[:10])
            return f"I couldn't determine which topics to search. Available topics include: {suggestions}"

        index = get_index()
        courses = load_multiple_topics(intent.topics, index, deduplicate=True)

        if not courses:
            suggestions = ", ".join(list(self._available_topics)[:10])
            return f"No courses found for: {', '.join(intent.topics)}. Available topics: {suggestions}"

        total_before_filter = len(courses)
        filters = intent.filters or {}

        courses = filter_courses(
            courses,
            min_rating=filters.get("min_rating"),
            max_price=filters.get("max_price"),
            level=filters.get("level"),
            is_free=filters.get("is_free"),
            min_duration=filters.get("min_duration"),
            max_duration=filters.get("max_duration"),
        )

        if not courses:
            filter_desc = describe_filters(filters)
            return f"No courses match your criteria ({filter_desc}). Found {total_before_filter} courses but none matched filters."

        limit = int(filters.get("limit") or 10)
        state.last_search_results = courses
        state.last_topic = intent.topics[0] if intent.topics else ""

        courses_text = format_courses_for_llm(courses)
        filter_summary = describe_filters(filters)

        prompt = get_analysis_prompt().format(
            user_query=user_message,
            course_data=f"Topics: {', '.join(intent.topics)}\nFilters: {filter_summary}\nTotal: {len(courses)}\nRequested: Top {limit}\n\n{courses_text}"
        )

        try:
            return await self._llm.call(
                get_response_prompt(intent.intent),
                prompt,
                temperature=0.4,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Search handler LLM failed: {e}")
            return f"Here are the matching courses:\n{courses_text}"

    @traceable(name="handle_top_valuable", run_type="chain")
    async def handle_top_valuable(
        self,
        intent: IntentClassification,
        user_message: str,
        state: ConversationState,
        conversation_history: str = "",
    ) -> str:
        """Handle top/valuable courses request.

        Args:
            intent: Classified intent
            user_message: Original user message
            state: Conversation state
            conversation_history: Optional history

        Returns:
            Response with top courses
        """
        filters = intent.filters or {}
        message_lower = user_message.lower()

        # Infer filters from message
        if "free" in message_lower or filters.get("is_free"):
            if not filters.get("is_free"):
                filters["is_free"] = True
        elif "beginner" in message_lower or filters.get("level") == "beginner":
            if not filters.get("level"):
                filters["level"] = "beginner"

        limit = int(filters.get("limit") or 10)
        index = get_index()

        if intent.topics:
            courses = load_multiple_topics(intent.topics, index, deduplicate=True)
        else:
            popular = ["python", "javascript", "data-science", "machine-learning", "web-development"]
            validated = validate_topics(popular)
            courses = load_multiple_topics(validated, index, deduplicate=True)

        if courses:
            courses = filter_courses(
                courses,
                min_rating=filters.get("min_rating"),
                max_price=filters.get("max_price"),
                level=filters.get("level"),
                is_free=filters.get("is_free"),
                min_duration=filters.get("min_duration"),
                max_duration=filters.get("max_duration"),
            )

        if not courses:
            return "No courses match your criteria. Try relaxing your filters."

        state.last_search_results = courses
        courses_text = format_courses_for_llm(courses)
        filter_summary = describe_filters(filters)

        prompt = get_analysis_prompt().format(
            user_query=user_message,
            course_data=f"Topics: {', '.join(intent.topics) if intent.topics else 'popular'}\nFilters: {filter_summary}\nTotal: {len(courses)}\nRequested: Top {limit}\n\n{courses_text}"
        )

        try:
            return await self._llm.call(
                get_response_prompt("top_valuable"),
                prompt,
                temperature=0.4,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Top valuable LLM failed: {e}")
            return f"Here are the courses:\n{courses_text}"

    @traceable(name="handle_stats", run_type="chain")
    async def handle_stats(
        self,
        intent: IntentClassification,
        user_message: str,
        conversation_history: str = "",
    ) -> str:
        """Handle statistics queries.

        Args:
            intent: Classified intent
            user_message: Original user message
            conversation_history: Optional history

        Returns:
            Statistics response
        """
        if intent.topics:
            stats_text = ""
            for topic in intent.topics:
                stats = get_topic_stats(topic)
                stats_text += f"""
{stats.topic}:
- Total courses: {stats.course_count}
- Average rating: {stats.avg_rating:.2f}
- Average price: ${stats.avg_price:.2f}
- Free courses: {stats.free_courses}
- Beginner courses: {stats.beginner_courses}
"""
        else:
            available = get_available_topics()
            total_courses = sum(t['course_count'] for t in available)
            stats_text = f"""
Knowledge Base Statistics:
- Total topics: {len(available)}
- Total courses: {total_courses}
- Top sections: {', '.join(set(t['section'] for t in available[:10]))}
"""

        prompt = f"User: {user_message}\n\nStatistics:\n{stats_text}"

        return await self._llm.call(
            get_response_prompt("stats"),
            prompt,
            temperature=0.3,
            conversation_history=conversation_history,
        )
