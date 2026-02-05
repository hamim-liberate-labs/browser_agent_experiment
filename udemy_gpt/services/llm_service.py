"""LLM service for AI-powered text generation.

This module provides the LLM client with rate limiting, retry logic,
and conversation history support.
"""

import asyncio
import logging
import time
from typing import Optional

from langchain_openai import ChatOpenAI
from langsmith import traceable

from udemy_gpt.config import settings
from udemy_gpt.exceptions import LLMError

logger = logging.getLogger(__name__)

# Global client instance
_llm_client: Optional[ChatOpenAI] = None


def get_client() -> ChatOpenAI:
    """Get or create LLM client singleton.

    Returns:
        ChatOpenAI client instance

    Raises:
        LLMError: If API key is not configured
    """
    global _llm_client

    if _llm_client is None:
        llm_settings = settings.llm

        try:
            api_key = llm_settings.get_api_key()
        except ValueError as e:
            raise LLMError(str(e))

        _llm_client = ChatOpenAI(
            base_url=llm_settings.base_url,
            api_key=api_key,
            model=llm_settings.model,
        )
        logger.info(f"LLM client initialized: {llm_settings.model}")

    return _llm_client


class LLMService:
    """LLM service with rate limiting and retry logic.

    Provides a high-level interface for making LLM calls with
    automatic rate limiting and retry on failures.
    """

    def __init__(self):
        """Initialize the LLM service."""
        self._last_call: float = 0
        self._llm_settings = settings.llm

    async def _rate_limit(self) -> None:
        """Apply rate limiting between calls."""
        elapsed = time.time() - self._last_call
        delay = self._llm_settings.rate_limit_delay
        if elapsed < delay:
            await asyncio.sleep(delay - elapsed)
        self._last_call = time.time()

    @traceable(name="llm_call", run_type="llm")
    async def call(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: Optional[float] = None,
        conversation_history: Optional[str] = None,
    ) -> str:
        """Make an LLM call with retry logic.

        Args:
            system_prompt: System message setting context
            user_prompt: User message/query
            temperature: Sampling temperature (0-2)
            conversation_history: Optional previous conversation

        Returns:
            LLM response text

        Raises:
            LLMError: If all retries fail
        """
        await self._rate_limit()

        llm = get_client()
        temp = temperature if temperature is not None else self._llm_settings.default_temperature

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history and settings.conversation.include_history_in_prompt:
            messages.append({
                "role": "system",
                "content": f"Previous conversation:\n{conversation_history}"
            })

        messages.append({"role": "user", "content": user_prompt})

        last_error = None
        for attempt in range(self._llm_settings.max_retries):
            try:
                response = await llm.ainvoke(messages, temperature=temp)
                return response.content
            except Exception as e:
                last_error = e
                logger.warning(f"LLM call failed (attempt {attempt + 1}): {e}")
                if attempt < self._llm_settings.max_retries - 1:
                    await asyncio.sleep(
                        self._llm_settings.retry_delay * (attempt + 1)
                    )

        logger.error(f"All LLM retries failed: {last_error}")
        raise LLMError(f"LLM call failed after {self._llm_settings.max_retries} attempts: {last_error}")


def reset_client() -> None:
    """Reset the LLM client (for testing or reconfiguration)."""
    global _llm_client
    _llm_client = None
    logger.info("LLM client reset")
