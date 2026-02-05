"""Services layer for Udemy GPT.

This module provides business logic services:
- LLM service for AI text generation
- Browser service for live course fetching
- Course service for search, filter, rank
- Intent service for query classification
"""

from udemy_gpt.services.llm_service import LLMService, get_client, reset_client
from udemy_gpt.services.browser_service import (
    fetch_course_details,
    close_browser,
    get_browser_context,
    STEALTH_AVAILABLE,
)
from udemy_gpt.services.course_service import (
    filter_courses,
    rank_courses,
    get_topic_stats,
    compare_topics,
    search_courses,
    get_top_courses_global,
)
from udemy_gpt.services.intent_service import IntentService

__all__ = [
    # LLM Service
    "LLMService",
    "get_client",
    "reset_client",
    # Browser Service
    "fetch_course_details",
    "close_browser",
    "get_browser_context",
    "STEALTH_AVAILABLE",
    # Course Service
    "filter_courses",
    "rank_courses",
    "get_topic_stats",
    "compare_topics",
    "search_courses",
    "get_top_courses_global",
    # Intent Service
    "IntentService",
]
