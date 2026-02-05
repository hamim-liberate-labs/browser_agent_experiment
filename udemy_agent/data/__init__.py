"""Data access layer for Udemy Agent."""

from udemy_agent.data.knowledge_base import (
    UDEMY_KNOWLEDGE,
    BROWSING_PATTERNS,
    FILTER_SELECTORS,
    get_action_for_intent,
    get_topic_url,
    get_search_url,
    normalize_topic_name,
)

__all__ = [
    "UDEMY_KNOWLEDGE",
    "BROWSING_PATTERNS",
    "FILTER_SELECTORS",
    "get_action_for_intent",
    "get_topic_url",
    "get_search_url",
    "normalize_topic_name",
]
