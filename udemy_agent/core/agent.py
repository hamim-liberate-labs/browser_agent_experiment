"""Main UdemyAgent class for course discovery."""

import logging
from typing import Any, Dict, List, Optional

from langsmith import traceable

from udemy_agent.core.workflows import build_chat_workflow
from udemy_agent.models import UdemyChatState
from udemy_agent.services.browser_service import get_browser_service

logger = logging.getLogger("udemy_agent")


class UdemyAgent:
    """Main interface for the Udemy Course Discovery Agent.

    This agent uses LangGraph workflows to orchestrate:
    - Intent classification
    - Browser automation
    - Response synthesis

    Usage:
        agent = UdemyAgent()
        response = await agent.chat("Find Python courses")
        await agent.close()
    """

    def __init__(self):
        """Initialize the agent."""
        self.chat_workflow = build_chat_workflow().compile()
        self.conversation_history: List[Dict[str, str]] = []
        self.last_search_results: Optional[List[Dict[str, Any]]] = None

    @traceable(name="udemy_agent_chat", run_type="chain")
    async def chat(self, user_message: str) -> str:
        """Process a user message and return a response.

        Args:
            user_message: User's input message

        Returns:
            Agent's response string
        """
        logger.info(f"User message: {user_message}")
        self.conversation_history.append({"role": "user", "content": user_message})

        initial_state = UdemyChatState(
            messages=self.conversation_history.copy(),
            last_search_results=self.last_search_results,
        )

        final_state = None
        async for event in self.chat_workflow.astream(initial_state):
            if isinstance(event, dict):
                for node_name, node_output in event.items():
                    if isinstance(node_output, dict):
                        if final_state is None:
                            final_state = node_output
                        else:
                            final_state.update(node_output)

        # Update cached search results
        if final_state and final_state.get("last_search_results"):
            self.last_search_results = final_state["last_search_results"]

        response = (
            final_state.get("response", "I'm sorry, I couldn't process your request.")
            if final_state else "Error processing request"
        )

        self.conversation_history.append({"role": "assistant", "content": response})
        return response

    def clear_history(self):
        """Clear conversation history and cached results."""
        self.conversation_history = []
        self.last_search_results = None
        logger.info("Conversation history cleared")

    async def close(self):
        """Clean up resources."""
        browser = get_browser_service()
        await browser.close()
        logger.info("Agent resources cleaned up")
