"""Udemy Agent - Multi-Agent System for Udemy Course Discovery.

This module provides a multi-agent system using LangGraph for discovering
Udemy courses through browser automation.

Usage:
    # CLI
    python -m udemy_agent
    udemy-agent

    # Programmatic
    from udemy_agent import UdemyAgent

    agent = UdemyAgent()
    response = await agent.chat("Find Python courses")
    await agent.close()
"""

from udemy_agent.core import UdemyAgent
from udemy_agent.config import settings
from udemy_agent.exceptions import (
    AgentError,
    LLMError,
    BrowserError,
    WorkflowError,
)
from udemy_agent.models import (
    BrowserFilters,
    UdemyChatState,
    UdemyBrowserState,
)

__version__ = "1.0.0"
__all__ = [
    # Main
    "UdemyAgent",
    "settings",
    # Exceptions
    "AgentError",
    "LLMError",
    "BrowserError",
    "WorkflowError",
    # Models
    "BrowserFilters",
    "UdemyChatState",
    "UdemyBrowserState",
]
