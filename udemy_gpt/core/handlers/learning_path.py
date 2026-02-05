"""Learning path handler.

Handles learning_path intent for career-oriented course recommendations.
"""

import logging
from typing import Dict, List, Set

from langsmith import traceable

from udemy_gpt.data import get_index, load_multiple_topics, validate_topics, parse_rating, parse_duration
from udemy_gpt.models import IntentClassification, ConversationState
from udemy_gpt.prompts import get_response_prompt
from udemy_gpt.services import LLMService

logger = logging.getLogger(__name__)

# Career path mappings
CAREER_PATHS: Dict[str, List[str]] = {
    "full-stack": ["html", "css", "javascript", "react", "nodejs", "sql", "docker"],
    "data-scientist": ["python", "sql", "statistics", "data-science", "machine-learning", "deep-learning"],
    "ml-engineer": ["python", "machine-learning", "deep-learning", "tensorflow", "data-science"],
    "ai-engineer": ["python", "machine-learning", "deep-learning", "nlp", "artificial-intelligence"],
    "web-developer": ["html", "css", "javascript", "react", "web-development"],
    "frontend": ["html", "css", "javascript", "react", "typescript"],
    "backend": ["python", "nodejs", "sql", "docker", "aws"],
    "mobile": ["react-native", "flutter", "android", "ios"],
    "devops": ["linux", "docker", "kubernetes", "aws", "terraform"],
    "cloud": ["aws", "docker", "kubernetes", "python", "linux"],
}


class LearningPathHandler:
    """Handler for learning path intent."""

    def __init__(self, llm_service: LLMService, available_topics: Set[str]):
        """Initialize learning path handler.

        Args:
            llm_service: LLM service for generating responses
            available_topics: Set of available topic slugs
        """
        self._llm = llm_service
        self._available_topics = available_topics

    def _detect_career_path(self, goal: str) -> List[str]:
        """Detect career path from goal string.

        Args:
            goal: User's career goal

        Returns:
            List of relevant topic slugs
        """
        goal_lower = goal.lower()

        for key, path_topics in CAREER_PATHS.items():
            if key.replace("-", " ") in goal_lower or key.replace("-", "") in goal_lower:
                return path_topics

        return []

    @traceable(name="handle_learning_path", run_type="chain")
    async def handle_learning_path(
        self,
        intent: IntentClassification,
        user_message: str,
        state: ConversationState,
        conversation_history: str = "",
    ) -> str:
        """Handle learning path recommendations.

        Args:
            intent: Classified intent with goal
            user_message: Original user message
            state: Conversation state
            conversation_history: Optional history

        Returns:
            Learning path response with courses
        """
        goal = intent.goal or user_message

        # Detect topics from career path
        topics = self._detect_career_path(goal)

        if not topics:
            topics = intent.topics if intent.topics else ["python", "javascript", "web-development"]

        validated_topics = validate_topics(topics)
        if not validated_topics:
            return f"No courses found for that path. Available: {', '.join(list(self._available_topics)[:10])}"

        index = get_index()
        all_courses = load_multiple_topics(validated_topics, index, deduplicate=True)

        # Get top courses per topic
        path_courses = []
        for topic in validated_topics:
            topic_courses = [c for c in all_courses if c.get("topic") == topic]
            if topic_courses:
                path_courses.extend(topic_courses[:3])

        if not path_courses:
            return "No suitable courses found for that learning path."

        state.last_search_results = path_courses

        # Format path text
        path_text = (
            f"**Career Goal:** {goal}\n\n"
            f"**Topics:** {', '.join(validated_topics)}\n\n---\n\n"
            f"## Courses by Topic\n"
        )

        for topic in validated_topics:
            topic_courses = [c for c in path_courses if c.get("topic") == topic]
            if topic_courses:
                path_text += f"\n### {topic.upper()}\n"
                for c in topic_courses:
                    url = c.get('url', '')
                    url_display = f"[Enroll Here]({url})" if url else "N/A"
                    path_text += f"""
**{c.get('title', 'N/A')}**
| Attribute | Value |
|-----------|-------|
| **URL** | {url_display} |
| **Instructor** | {c.get('instructor', 'N/A')} |
| **Rating** | {parse_rating(c.get('rating', '0'))}/5 ({c.get('reviews_count', 'N/A')} reviews) |
| **Price** | {c.get('price', 'N/A')} |
| **Duration** | {parse_duration(c.get('duration', '0'))} hours |
| **Level** | {c.get('level', 'N/A')} |
"""

        prompt = (
            f"User goal: {user_message}\n\n{path_text}\n\n"
            f"Create structured learning path with best course per topic."
        )

        try:
            return await self._llm.call(
                get_response_prompt("learning_path"),
                prompt,
                temperature=0.4,
                conversation_history=conversation_history,
            )
        except Exception as e:
            logger.error(f"Learning path LLM failed: {e}")
            return f"Courses for your learning path:\n{path_text}"
