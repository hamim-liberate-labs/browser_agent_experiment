"""Data access layer for Udemy GPT.

This module provides:
- CSV data loading and caching (repository)
- Topic indexing and validation (topic_index)
"""

from udemy_gpt.data.repository import (
    # Parsing utilities
    parse_number,
    parse_price,
    parse_duration,
    parse_rating,
    # Loading functions
    load_csv,
    load_topic_courses,
    load_multiple_topics,
    load_all_courses,
    # Cache management
    clear_cache,
    get_cache_stats,
    # Course search
    search_course_by_name,
    generate_course_url,
)

from udemy_gpt.data.topic_index import (
    # Index management
    build_index,
    get_index,
    get_topic_list_for_llm,
    reset_index,
    # Topic queries
    get_available_slugs,
    get_available_topics,
    search_topics,
    # Validation
    validate_topics,
)

__all__ = [
    # Repository - Parsing
    "parse_number",
    "parse_price",
    "parse_duration",
    "parse_rating",
    # Repository - Loading
    "load_csv",
    "load_topic_courses",
    "load_multiple_topics",
    "load_all_courses",
    # Repository - Cache
    "clear_cache",
    "get_cache_stats",
    # Repository - Course search
    "search_course_by_name",
    "generate_course_url",
    # Topic Index
    "build_index",
    "get_index",
    "get_topic_list_for_llm",
    "reset_index",
    "get_available_slugs",
    "get_available_topics",
    "search_topics",
    "validate_topics",
]
