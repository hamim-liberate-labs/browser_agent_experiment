"""Chat handler for general conversation.

Handles chat intent for general queries and conversation.
"""

import logging

from udemy_gpt.data import get_available_topics
from udemy_gpt.prompts import get_response_prompt
from udemy_gpt.services import LLMService

logger = logging.getLogger(__name__)


class ChatHandler:
    """Handler for general chat intent."""

    def __init__(self, llm_service: LLMService):
        """Initialize chat handler.

        Args:
            llm_service: LLM service for generating responses
        """
        self._llm = llm_service

    async def handle_chat(
        self,
        user_message: str,
        conversation_history: str = "",
    ) -> str:
        """Handle general chat/conversation.

        Args:
            user_message: User's message
            conversation_history: Optional history

        Returns:
            Conversational response
        """
        available = get_available_topics()[:10]
        topics_preview = ", ".join(t['slug'] for t in available)

        context_section = (
            f"\n\nConversation context:\n{conversation_history}"
            if conversation_history else ""
        )

        prompt = f"""User: {user_message}{context_section}

I'm a Udemy course discovery assistant. I help with:
- Finding courses on specific topics
- Comparing courses or topics
- Recommending top courses
- Creating learning paths
- Getting course details

Available topics: {topics_preview}, and more."""

        try:
            return await self._llm.call(
                get_response_prompt("chat"),
                prompt,
                temperature=0.5,
            )
        except Exception as e:
            logger.error(f"Chat LLM failed: {e}")
            return (
                f"Hello! I'm your Udemy course assistant. "
                f"I can help you find courses on topics like {topics_preview}."
            )
