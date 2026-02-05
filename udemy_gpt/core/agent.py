"""Udemy GPT Agent - Main orchestrator for course discovery.

This module contains the main UdemyGPT class that orchestrates
all the services and handlers to provide a conversational
interface for course discovery.
"""

import logging
from typing import Any, Dict, Optional

from langsmith import traceable

from udemy_gpt.config import settings
from udemy_gpt.data import build_index, get_available_slugs
from udemy_gpt.models import ConversationState
from udemy_gpt.services import LLMService, IntentService, close_browser
from udemy_gpt.core.handlers import (
    SearchHandler,
    CompareHandler,
    DetailsHandler,
    LearningPathHandler,
    ChatHandler,
)
from udemy_gpt.utils import format_conversation_context

logger = logging.getLogger(__name__)


class UdemyGPT:
    """Main Udemy GPT agent for course discovery.

    This class orchestrates all services and handlers to provide
    a conversational interface for discovering Udemy courses.

    Attributes:
        state: Conversation state tracking messages and search results

    Example:
        ```python
        agent = UdemyGPT()
        response = await agent.chat("Find Python courses for beginners")
        print(response)
        await agent.close()
        ```
    """

    def __init__(self):
        """Initialize the Udemy GPT agent."""
        self.state = ConversationState()
        self._available_topics: set = set()

        logger.info("Initializing Udemy GPT...")

        # Build topic index
        build_index()
        self._available_topics = get_available_slugs()

        # Initialize services
        self._llm_service = LLMService()
        self._intent_service = IntentService(self._llm_service)

        # Initialize handlers
        self._search_handler = SearchHandler(self._llm_service, self._available_topics)
        self._compare_handler = CompareHandler(self._llm_service)
        self._details_handler = DetailsHandler(self._llm_service)
        self._learning_path_handler = LearningPathHandler(self._llm_service, self._available_topics)
        self._chat_handler = ChatHandler(self._llm_service)

        logger.info(f"Initialized with {len(self._available_topics)} available topics")

    def _get_conversation_history(self) -> str:
        """Get formatted conversation history for context.

        Returns:
            Formatted conversation history string
        """
        if not settings.conversation.include_history_in_prompt:
            return ""
        return format_conversation_context(
            self.state.messages,
            settings.conversation.max_history_messages
        )

    @traceable(name="chat", run_type="chain")
    async def chat(self, user_message: str) -> str:
        """Main chat interface.

        Process a user message and return an appropriate response.
        The message is classified by intent and routed to the
        appropriate handler.

        Args:
            user_message: User's input message

        Returns:
            Agent's response text
        """
        self.state.add_message("user", user_message)
        history = self._get_conversation_history()

        try:
            # Classify intent
            intent = await self._intent_service.classify(
                user_message,
                self.state.last_search_results
            )
            self.state.current_intent = intent.intent

            # Route to appropriate handler
            if intent.intent in ("search", "recommend", "filter"):
                response = await self._search_handler.handle_search(
                    intent, user_message, self.state, history
                )
            elif intent.intent == "compare":
                response = await self._compare_handler.handle_compare(
                    intent, user_message, self.state, history
                )
            elif intent.intent in ("compare_topics", "cross_topic_analysis"):
                response = await self._compare_handler.handle_compare_topics(
                    intent, user_message, history
                )
            elif intent.intent == "details":
                response = await self._details_handler.handle_details(
                    intent, user_message, self.state, history
                )
            elif intent.intent == "top_valuable":
                response = await self._search_handler.handle_top_valuable(
                    intent, user_message, self.state, history
                )
            elif intent.intent == "learning_path":
                response = await self._learning_path_handler.handle_learning_path(
                    intent, user_message, self.state, history
                )
            elif intent.intent == "stats":
                response = await self._search_handler.handle_stats(
                    intent, user_message, history
                )
            else:
                response = await self._chat_handler.handle_chat(
                    user_message, history
                )

        except Exception as e:
            logger.error(f"Error processing chat: {e}", exc_info=True)
            response = "I encountered an error. Please try again."

        self.state.add_message("assistant", response)

        # Trim history if needed
        max_history = settings.conversation.max_history_messages * 2
        self.state.trim_history(max_history)

        return response

    def clear_history(self) -> None:
        """Clear conversation history and search results."""
        self.state.clear()
        logger.info("Conversation history cleared")

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics.

        Returns:
            Dictionary with session statistics
        """
        return {
            "messages_count": len(self.state.messages),
            "last_search_count": len(self.state.last_search_results),
            "current_intent": self.state.current_intent,
            "last_topic": self.state.last_topic,
            "available_topics": len(self._available_topics),
        }

    async def close(self) -> None:
        """Cleanup resources.

        Call this method when done using the agent to properly
        close browser and other resources.
        """
        logger.info("Closing Udemy GPT...")
        await close_browser()
