"""Comparison handler for courses and topics.

Handles compare and compare_topics intents.
"""

import logging
import re
from typing import List

from langsmith import traceable

from udemy_gpt.models import IntentClassification, ConversationState
from udemy_gpt.prompts import get_response_prompt
from udemy_gpt.services import compare_topics, LLMService
from udemy_gpt.utils import format_comparison

logger = logging.getLogger(__name__)


class CompareHandler:
    """Handler for comparison intents."""

    def __init__(self, llm_service: LLMService):
        """Initialize compare handler.

        Args:
            llm_service: LLM service for generating responses
        """
        self._llm = llm_service

    @traceable(name="handle_compare", run_type="chain")
    async def handle_compare(
        self,
        intent: IntentClassification,
        user_message: str,
        state: ConversationState,
        conversation_history: str = "",
    ) -> str:
        """Handle course comparison.

        Args:
            intent: Classified intent
            user_message: Original user message
            state: Conversation state with search results
            conversation_history: Optional history

        Returns:
            Comparison response
        """
        if not state.last_search_results:
            return "Please search for courses first, then I can compare them."

        # Extract course indices from message
        indices = re.findall(r'course\s*(\d+)', user_message.lower())
        if not indices:
            indices = re.findall(r'(\d+)', user_message)

        if len(indices) < 2:
            return "Please specify which courses to compare (e.g., 'compare course 1 and 2')."

        courses_to_compare = []
        for idx_str in indices[:3]:  # Max 3 courses
            idx = int(idx_str) - 1
            if 0 <= idx < len(state.last_search_results):
                courses_to_compare.append(state.last_search_results[idx])

        if len(courses_to_compare) < 2:
            return "I couldn't find those courses. Please use valid course numbers."

        comparison_text = format_comparison(courses_to_compare)
        prompt = f"User wants to compare:\n{comparison_text}\nProvide detailed comparison and recommendation."

        return await self._llm.call(
            get_response_prompt("compare"),
            prompt,
            temperature=0.3,
            conversation_history=conversation_history,
        )

    @traceable(name="handle_compare_topics", run_type="chain")
    async def handle_compare_topics(
        self,
        intent: IntentClassification,
        user_message: str,
        conversation_history: str = "",
    ) -> str:
        """Handle topic comparison.

        Args:
            intent: Classified intent with topics to compare
            user_message: Original user message
            conversation_history: Optional history

        Returns:
            Topic comparison response
        """
        if len(intent.topics) < 2:
            return "Please specify topics to compare (e.g., 'Python vs JavaScript')."

        try:
            comparison = compare_topics(intent.topics)
        except Exception as e:
            logger.error(f"Topic comparison failed: {e}")
            return "I couldn't compare those topics."

        topics_with_data = [
            t for t, s in comparison.topics.items()
            if s.course_count > 0
        ]
        if len(topics_with_data) < 2:
            missing = [t for t in intent.topics if t not in topics_with_data]
            return f"Missing data for: {', '.join(missing)}. Try different topics."

        # Format topic statistics
        topics_text = ""
        for topic, stats in comparison.topics.items():
            top_course_info = (
                f"{stats.top_course.title} ({stats.top_course.rating}/5)"
                if stats.top_course else "N/A"
            )
            topics_text += f"""
### {topic.upper()}
| Metric | Value |
|--------|-------|
| **Total Courses** | {stats.course_count} |
| **Average Rating** | {stats.avg_rating:.2f}/5 |
| **Average Price** | ${stats.avg_price:.2f} |
| **Free Courses** | {stats.free_courses} |
| **Beginner Courses** | {stats.beginner_courses} |
| **Top Course** | {top_course_info} |
"""

        prompt = (
            f"User query: {user_message}\n\n"
            f"Topic data:\n{topics_text}\n\n"
            f"Analysis: {comparison.recommendation}"
        )

        try:
            return await self._llm.call(
                get_response_prompt("compare_topics"),
                prompt,
                temperature=0.3,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Compare topics LLM failed: {e}")
            return f"Comparison data:\n{topics_text}\n\n{comparison.recommendation}"
