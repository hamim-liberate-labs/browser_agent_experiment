"""Intent classification service.

This module handles user intent classification using LLM,
extracting topics, filters, and determining the appropriate
action for user queries.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from langsmith import traceable

from udemy_gpt.data import get_topic_list_for_llm, validate_topics
from udemy_gpt.models import IntentClassification
from udemy_gpt.prompts import get_intent_prompt
from udemy_gpt.services.llm_service import LLMService
from udemy_gpt.utils import extract_json, parse_filters

logger = logging.getLogger(__name__)


class IntentService:
    """Service for classifying user intents.

    Uses LLM to analyze user queries and extract:
    - Intent type (search, compare, details, etc.)
    - Relevant topics
    - Search filters
    - Course references
    """

    def __init__(self, llm_service: Optional[LLMService] = None):
        """Initialize intent service.

        Args:
            llm_service: Optional LLM service instance (creates one if not provided)
        """
        self._llm = llm_service or LLMService()

    @traceable(name="classify_intent", run_type="chain")
    async def classify(
        self,
        user_message: str,
        previous_results: Optional[List[Dict[str, Any]]] = None,
    ) -> IntentClassification:
        """Classify user intent from message.

        Args:
            user_message: User's query text
            previous_results: Optional previous search results for context

        Returns:
            IntentClassification with extracted intent and parameters
        """
        topic_list = get_topic_list_for_llm()

        # Build context from previous results
        context = ""
        if previous_results:
            context = "\n\nPrevious search results:\n"
            for i, course in enumerate(previous_results[:5], 1):
                context += f"{i}. {course.get('title', 'Unknown')}\n"

        system_prompt = get_intent_prompt().format(topic_list=topic_list)
        user_prompt = f"User query: {user_message}{context}"

        try:
            response = await self._llm.call(system_prompt, user_prompt)
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return IntentClassification(intent="chat")

        return self._parse_response(response)

    def _parse_response(self, response: str) -> IntentClassification:
        """Parse LLM response into IntentClassification.

        Args:
            response: Raw LLM response text

        Returns:
            Parsed IntentClassification
        """
        try:
            json_str = extract_json(response)
            data = json.loads(json_str)

            raw_topics = data.get("selected_topics", [])
            validated_topics = validate_topics(raw_topics)
            filters = parse_filters(data.get("filters", {}))
            intent = data.get("intent", "chat")
            needs_browser = data.get("needs_browser", False)

            # Handle course_reference - ensure it's an int or None
            course_ref = data.get("course_reference")
            if course_ref is not None:
                if isinstance(course_ref, int):
                    pass  # Already an int
                elif isinstance(course_ref, str):
                    # Try to parse as int, otherwise default to 1 (first course)
                    try:
                        course_ref = int(course_ref)
                    except ValueError:
                        # LLM returned course title instead of number, default to 1
                        logger.warning(f"course_reference is a string '{course_ref}', defaulting to 1")
                        course_ref = 1
                else:
                    course_ref = None

            logger.info(
                f"Intent: {intent}, Topics: {validated_topics}, Browser: {needs_browser}"
            )

            return IntentClassification(
                intent=intent,
                topics=validated_topics,
                filters=filters,
                course_reference=course_ref,
                needs_browser=needs_browser,
                goal=data.get("goal"),
            )
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse intent response: {e}")
            return IntentClassification(intent="chat")
