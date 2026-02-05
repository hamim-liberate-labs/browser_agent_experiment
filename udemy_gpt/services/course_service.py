"""Course service for searching, filtering, and ranking courses.

This module provides the business logic for course operations including
filtering, ranking, statistics, and comparison.
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

from langsmith import traceable

from udemy_gpt.data import (
    get_index,
    load_multiple_topics,
    load_all_courses,
    load_topic_courses,
    search_topics,
    parse_rating,
    parse_price,
    parse_duration,
    parse_number,
)
from udemy_gpt.models import Course, TopicStats, TopicComparison

logger = logging.getLogger(__name__)


# =============================================================================
# Filtering
# =============================================================================

@traceable(name="filter_courses", run_type="tool")
def filter_courses(
    courses: List[Dict],
    min_rating: Optional[float] = None,
    max_price: Optional[float] = None,
    level: Optional[str] = None,
    is_free: Optional[bool] = None,
    min_duration: Optional[float] = None,
    max_duration: Optional[float] = None,
    bestseller_only: bool = False,
) -> List[Dict]:
    """Filter courses by multiple criteria.

    Args:
        courses: List of course dictionaries
        min_rating: Minimum rating threshold
        max_price: Maximum price threshold
        level: Required level (beginner, intermediate, advanced)
        is_free: If True, only free courses; if False, only paid
        min_duration: Minimum duration in hours
        max_duration: Maximum duration in hours
        bestseller_only: If True, only bestseller courses

    Returns:
        Filtered list of courses
    """
    filtered = []

    for course in courses:
        # Rating filter
        if min_rating:
            rating = parse_rating(course.get("rating", "0"))
            if rating < min_rating:
                continue

        # Price filter
        price = parse_price(course.get("price", "$99"))
        if max_price is not None and price > max_price:
            continue
        if is_free is not None:
            if is_free and price > 0:
                continue
            if not is_free and price == 0:
                continue

        # Level filter
        if level:
            course_level = course.get("level", "").lower()
            if level.lower() not in course_level:
                continue

        # Duration filter
        duration = parse_duration(course.get("duration", "0"))
        if min_duration and duration < min_duration:
            continue
        if max_duration and duration > max_duration:
            continue

        # Bestseller filter
        if bestseller_only:
            is_bs = str(course.get("bestseller", "")).lower() in ("true", "yes", "1")
            if not is_bs:
                continue

        filtered.append(course)

    return filtered


# =============================================================================
# Ranking
# =============================================================================

@traceable(name="rank_courses", run_type="tool")
def rank_courses(
    courses: List[Dict],
    sort_by: str = "rating",
    limit: int = 10
) -> List[Dict]:
    """Rank courses by specified criteria.

    Args:
        courses: List of course dictionaries
        sort_by: Sort criterion (rating, reviews, price, price_desc, duration)
        limit: Maximum number of courses to return

    Returns:
        Sorted and limited list of courses
    """
    if sort_by == "rating":
        sorted_courses = sorted(
            courses,
            key=lambda x: (
                parse_rating(x.get("rating", "0")),
                parse_number(x.get("reviews_count", "0"))
            ),
            reverse=True
        )
    elif sort_by == "reviews":
        sorted_courses = sorted(
            courses,
            key=lambda x: parse_number(x.get("reviews_count", "0")),
            reverse=True
        )
    elif sort_by == "price":
        sorted_courses = sorted(
            courses,
            key=lambda x: parse_price(x.get("price", "$99"))
        )
    elif sort_by == "price_desc":
        sorted_courses = sorted(
            courses,
            key=lambda x: parse_price(x.get("price", "$99")),
            reverse=True
        )
    elif sort_by == "duration":
        sorted_courses = sorted(
            courses,
            key=lambda x: parse_duration(x.get("duration", "0")),
            reverse=True
        )
    else:
        # Default to rating
        sorted_courses = sorted(
            courses,
            key=lambda x: (
                parse_rating(x.get("rating", "0")),
                parse_number(x.get("reviews_count", "0"))
            ),
            reverse=True
        )

    return sorted_courses[:limit]


# =============================================================================
# Statistics
# =============================================================================

@traceable(name="get_topic_stats", run_type="tool")
def get_topic_stats(topic_slug: str) -> TopicStats:
    """Get statistics for a topic.

    Args:
        topic_slug: Topic identifier

    Returns:
        TopicStats object with aggregated statistics
    """
    index = get_index()
    topic_info = index.get(topic_slug, {})
    courses = load_topic_courses(topic_slug, topic_info)

    if not courses:
        return TopicStats(topic=topic_slug)

    ratings = [parse_rating(c.get("rating", "0")) for c in courses]
    prices = [parse_price(c.get("price", "$0")) for c in courses]
    reviews = [parse_number(c.get("reviews_count", "0")) for c in courses]

    # Find top course by rating and reviews
    top = max(
        courses,
        key=lambda x: (
            parse_rating(x.get("rating", "0")),
            parse_number(x.get("reviews_count", "0"))
        )
    )

    return TopicStats(
        topic=topic_slug,
        course_count=len(courses),
        avg_rating=sum(ratings) / len(ratings) if ratings else 0,
        avg_price=sum(prices) / len(prices) if prices else 0,
        total_reviews=sum(reviews),
        free_courses=len([c for c in courses if parse_price(c.get("price", "$99")) == 0]),
        beginner_courses=len([c for c in courses if "beginner" in c.get("level", "").lower()]),
        top_course=Course(
            title=top.get("title", ""),
            url=top.get("url", ""),
            rating=parse_rating(top.get("rating", "0")),
            reviews_count=parse_number(top.get("reviews_count", "0")),
            price=top.get("price", ""),
        ),
    )


@traceable(name="compare_topics", run_type="chain")
def compare_topics(topics: List[str]) -> TopicComparison:
    """Compare multiple topics.

    Args:
        topics: List of topic slugs to compare

    Returns:
        TopicComparison with stats and recommendation
    """
    stats = {}
    for topic in topics:
        stats[topic] = get_topic_stats(topic)

    recommendation = ""
    if len(stats) >= 2:
        sorted_topics = sorted(
            stats.items(),
            key=lambda x: (x[1].avg_rating * x[1].course_count, x[1].total_reviews),
            reverse=True
        )
        best = sorted_topics[0]
        recommendation = (
            f"{best[0]} has the strongest offerings with "
            f"{best[1].course_count} courses averaging {best[1].avg_rating:.1f} stars."
        )

    return TopicComparison(topics=stats, recommendation=recommendation)


# =============================================================================
# Search
# =============================================================================

@traceable(name="search_courses", run_type="chain")
def search_courses(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20
) -> Tuple[List[Dict], List[str]]:
    """Search for courses by query and filters.

    Args:
        query: Search query string
        filters: Optional filter criteria
        limit: Maximum results to return

    Returns:
        Tuple of (matching courses, matched topics)
    """
    index = get_index()
    matching_topics = search_topics(query)

    if not matching_topics:
        # Fallback to title/instructor search
        all_courses = load_all_courses(index)
        query_lower = query.lower()
        matching = [
            c for c in all_courses
            if query_lower in c.get("title", "").lower()
            or query_lower in c.get("instructor", "").lower()
        ]
        if matching:
            return rank_courses(matching, "rating", limit), []
        return [], []

    courses = load_multiple_topics(matching_topics, index)

    if filters:
        courses = filter_courses(
            courses,
            min_rating=filters.get("min_rating"),
            max_price=filters.get("max_price"),
            level=filters.get("level"),
            is_free=filters.get("is_free"),
            min_duration=filters.get("min_duration"),
            max_duration=filters.get("max_duration"),
            bestseller_only=filters.get("bestseller_only", False),
        )

    ranked = rank_courses(
        courses,
        filters.get("sort_by", "rating") if filters else "rating",
        limit
    )

    return ranked, matching_topics


@traceable(name="get_top_courses_global", run_type="chain")
def get_top_courses_global(n: int = 10, category: str = "best_overall") -> List[Dict]:
    """Get top courses across all topics.

    Args:
        n: Number of courses to return
        category: Category filter (best_free, best_value, most_popular,
                  highest_rated, best_for_beginners, best_overall)

    Returns:
        List of top courses
    """
    index = get_index()
    all_courses = load_all_courses(index)

    if category == "best_free":
        free_courses = filter_courses(all_courses, is_free=True)
        return rank_courses(free_courses, "rating", n)
    elif category == "best_value":
        affordable = filter_courses(all_courses, max_price=20)
        return rank_courses(affordable, "rating", n)
    elif category == "most_popular":
        return rank_courses(all_courses, "reviews", n)
    elif category == "highest_rated":
        high_rated = filter_courses(all_courses, min_rating=4.5)
        return rank_courses(high_rated, "rating", n)
    elif category == "best_for_beginners":
        beginner = filter_courses(all_courses, level="beginner")
        return rank_courses(beginner, "rating", n)
    else:
        return rank_courses(all_courses, "rating", n)
