"""LLM service for Udemy Agent."""

import logging
from typing import Dict, Optional

from langchain_openai import ChatOpenAI
from langsmith import traceable

from udemy_agent.config import get_llm_settings
from udemy_agent.exceptions import LLMError

logger = logging.getLogger("udemy_agent.llm")


class LLMService:
    """Manages LLM clients and calls."""

    def __init__(self):
        self._clients: Dict[str, ChatOpenAI] = {}
        self._settings = get_llm_settings()

    def get_client(self, model_name: Optional[str] = None) -> ChatOpenAI:
        """Get or create a ChatOpenAI client for the specified model.

        Args:
            model_name: Model name (uses active model if not specified)

        Returns:
            ChatOpenAI client instance
        """
        model_name = model_name or self._settings.active_model

        if model_name in self._clients:
            return self._clients[model_name]

        try:
            config = self._settings.get_model_config(model_name)
            api_key = self._settings.get_api_key(model_name)

            client = ChatOpenAI(
                base_url=config["base_url"],
                api_key=api_key,
                model=config["model"],
            )

            self._clients[model_name] = client
            logger.info(f"Initialized LLM client: {model_name}")
            return client

        except Exception as e:
            raise LLMError(f"Failed to initialize LLM client: {e}")

    @traceable(name="call_llm", run_type="llm")
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        model_name: Optional[str] = None,
    ) -> str:
        """Call the LLM with system and user prompts.

        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            temperature: Temperature (uses default if not specified)
            model_name: Model to use (uses active model if not specified)

        Returns:
            LLM response content
        """
        temperature = temperature if temperature is not None else self._settings.default_temperature
        client = self.get_client(model_name)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = await client.ainvoke(messages, temperature=temperature)
            return response.content
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise LLMError(f"LLM call failed: {e}")


# Global service instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get the global LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
