"""Data repository for CSV course data access.

This module handles all CSV file operations including loading, caching,
and parsing of course data.
"""

import csv
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from udemy_gpt.config import settings

logger = logging.getLogger(__name__)

# In-memory cache for loaded CSV data
_csv_cache: Dict[str, List[Dict]] = {}


# =============================================================================
# Parsing Utilities
# =============================================================================

def parse_number(value: str) -> int:
    """Parse number from string like '12,345' or '1.2M'.

    Args:
        value: String representation of number

    Returns:
        Parsed integer value, 0 if parsing fails
    """
    if not value:
        return 0
    value = str(value).strip().replace(",", "").replace("(", "").replace(")", "")
    if value.endswith("K"):
        return int(float(value[:-1]) * 1000)
    if value.endswith("M"):
        return int(float(value[:-1]) * 1000000)
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def parse_price(value: str) -> float:
    """Parse price from string like '$12.99' or 'Free'.

    Args:
        value: Price string

    Returns:
        Price as float, 0.0 for free or invalid
    """
    if not value:
        return 0.0
    value = str(value).strip().lower()
    if value == "free":
        return 0.0
    match = re.search(r"[\d.]+", value)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return 0.0
    return 0.0


def parse_duration(value: str) -> float:
    """Parse duration in hours from string.

    Args:
        value: Duration string (e.g., '10 hours', '30 min')

    Returns:
        Duration in hours
    """
    if not value:
        return 0.0
    value = str(value).lower().strip()
    match = re.search(r"([\d.]+)", value)
    if not match:
        return 0.0
    try:
        num = float(match.group(1))
    except ValueError:
        return 0.0
    if "min" in value:
        return round(num / 60, 2)
    return num


def parse_rating(value: str) -> float:
    """Parse rating from string.

    Args:
        value: Rating string (e.g., '4.5', '4.5 out of 5')

    Returns:
        Rating as float between 0-5
    """
    if not value:
        return 0.0
    value = str(value).strip()
    # Try direct float conversion
    try:
        rating = float(value)
        if 0 <= rating <= 5:
            return rating
    except (ValueError, TypeError):
        pass
    # Handle "X.X out of 5" format
    if "out of" in value.lower():
        match = re.search(r'(\d+\.?\d*)\s*out\s*of\s*5', value, re.IGNORECASE)
        if match:
            try:
                rating = float(match.group(1))
                if 0 <= rating <= 5:
                    return rating
            except ValueError:
                pass
    # Extract any decimal number between 0-5
    numbers = re.findall(r'(\d+\.?\d*)', value)
    for num_str in numbers:
        try:
            num = float(num_str)
            if 0 < num <= 5:
                return num
        except ValueError:
            continue
    return 0.0


# =============================================================================
# CSV Loading
# =============================================================================

def load_csv(file_path: Path) -> List[Dict[str, Any]]:
    """Load a CSV file into a list of dictionaries.

    Args:
        file_path: Path to CSV file

    Returns:
        List of row dictionaries
    """
    if not file_path.exists():
        logger.warning(f"CSV file not found: {file_path}")
        return []

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        logger.error(f"Error loading CSV {file_path}: {e}")
        return []


def load_topic_courses(topic_slug: str, topic_info: Dict[str, Any]) -> List[Dict]:
    """Load courses for a specific topic with caching.

    Args:
        topic_slug: Topic identifier
        topic_info: Topic metadata including file path

    Returns:
        List of course dictionaries
    """
    global _csv_cache

    if topic_slug in _csv_cache:
        return _csv_cache[topic_slug]

    if "full_path" not in topic_info:
        return []

    csv_path = Path(topic_info["full_path"])
    if not csv_path.exists():
        return []

    courses = []
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                row["topic"] = topic_slug
                row["section"] = topic_info.get("section", "")
                courses.append(row)
    except Exception as e:
        logger.error(f"Error loading {csv_path}: {e}")
        return []

    _csv_cache[topic_slug] = courses
    return courses


def load_multiple_topics(
    topics: List[str],
    topic_index: Dict[str, Dict],
    deduplicate: bool = True
) -> List[Dict]:
    """Load courses from multiple topics.

    Args:
        topics: List of topic slugs
        topic_index: Topic index dictionary
        deduplicate: Whether to remove duplicate courses

    Returns:
        Combined list of courses
    """
    all_courses = []
    seen_urls: Set[str] = set()

    for topic in topics:
        topic_info = topic_index.get(topic, {})
        courses = load_topic_courses(topic, topic_info)

        if deduplicate:
            for course in courses:
                url = course.get("url", "")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_courses.append(course)
                elif not url:
                    key = f"{course.get('title', '')}|{course.get('instructor', '')}"
                    if key not in seen_urls:
                        seen_urls.add(key)
                        all_courses.append(course)
        else:
            all_courses.extend(courses)

    return all_courses


def load_all_courses(topic_index: Dict[str, Dict]) -> List[Dict]:
    """Load all courses from all topics.

    Args:
        topic_index: Topic index dictionary

    Returns:
        All courses from all topics
    """
    all_courses = []
    for slug, info in topic_index.items():
        if "full_path" in info:
            courses = load_topic_courses(slug, info)
            all_courses.extend(courses)
    return all_courses


def clear_cache() -> None:
    """Clear the CSV cache."""
    global _csv_cache
    _csv_cache.clear()
    logger.info("CSV cache cleared")


def get_cache_stats() -> Dict[str, int]:
    """Get cache statistics.

    Returns:
        Dictionary with cache stats
    """
    return {
        "cached_topics": len(_csv_cache),
        "cached_courses": sum(len(courses) for courses in _csv_cache.values()),
    }


def _match_course_name(query: str, title: str) -> float:
    """Calculate match score between query and course title.

    Args:
        query: Search query (course name)
        title: Course title

    Returns:
        Match score (0.0 to 1.0)
    """
    query_lower = query.lower().strip()
    title_lower = title.lower().strip()

    # Exact match
    if query_lower == title_lower:
        return 1.0

    # Query is substring of title or vice versa
    if query_lower in title_lower:
        return 0.9
    if title_lower in query_lower:
        return 0.85

    # Word overlap matching
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    title_words = set(re.findall(r'\b\w+\b', title_lower))

    # Remove common stop words
    stop_words = {'the', 'a', 'an', 'in', 'on', 'to', 'for', 'of', 'and', 'with', 'from', 'course'}
    query_words = query_words - stop_words
    title_words = title_words - stop_words

    if not query_words or not title_words:
        return 0.0

    # Calculate Jaccard-like similarity
    overlap = query_words & title_words
    if not overlap:
        return 0.0

    # Score based on how many query words are in title
    query_coverage = len(overlap) / len(query_words)
    # Bonus for significant overlap
    if len(overlap) >= 3:
        return min(0.8, query_coverage)
    elif len(overlap) >= 2:
        return min(0.6, query_coverage)

    return query_coverage * 0.5


def search_course_by_name(
    course_name: str,
    topic_index: Dict[str, Dict],
    search_results: Optional[List[Dict]] = None,
) -> Optional[Dict]:
    """Search for a course by name in search results or knowledge base.

    Args:
        course_name: Course name/title to search for
        topic_index: Topic index dictionary
        search_results: Optional previous search results to check first

    Returns:
        Course dictionary if found, None otherwise
    """
    if not course_name:
        return None

    best_match = None
    best_score = 0.0
    min_score_threshold = 0.5  # Minimum score to consider a match

    # Helper to check a list of courses
    def check_courses(courses: List[Dict]) -> None:
        nonlocal best_match, best_score
        for course in courses:
            title = course.get("title", "")
            if not title:
                continue
            score = _match_course_name(course_name, title)
            if score > best_score:
                best_score = score
                best_match = course
                # Early exit for high confidence match
                if score >= 0.9:
                    return

    # First check in previous search results (highest priority)
    if search_results:
        check_courses(search_results)
        if best_score >= 0.9:
            logger.info(f"Found course in search results with score {best_score:.2f}")
            return best_match

    # Search in cached courses
    for courses in _csv_cache.values():
        check_courses(courses)
        if best_score >= 0.9:
            logger.info(f"Found course in cache with score {best_score:.2f}")
            return best_match

    # Load topics matching likely keywords in course name
    name_lower = course_name.lower()
    likely_topics = []
    for slug in topic_index.keys():
        slug_clean = slug.replace('-', ' ')
        if slug_clean in name_lower or any(word in name_lower for word in slug_clean.split()):
            likely_topics.append(slug)

    # Search in likely topics first
    for slug in likely_topics:
        if slug not in _csv_cache:
            info = topic_index.get(slug, {})
            if "full_path" in info:
                courses = load_topic_courses(slug, info)
                check_courses(courses)
                if best_score >= 0.9:
                    logger.info(f"Found course in topic '{slug}' with score {best_score:.2f}")
                    return best_match

    # Return best match if above threshold
    if best_match and best_score >= min_score_threshold:
        logger.info(f"Best match found with score {best_score:.2f}: {best_match.get('title', '')[:60]}")
        return best_match

    logger.info(f"No matching course found for '{course_name}' (best score: {best_score:.2f})")
    return None


def generate_course_url(course_name: str) -> str:
    """Generate a Udemy course URL from course name.

    Args:
        course_name: Course name/title

    Returns:
        Generated Udemy course URL
    """
    # Convert to URL slug format
    slug = course_name.lower()
    # Remove special characters
    slug = re.sub(r'[^\w\s-]', '', slug)
    # Replace spaces with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Trim hyphens from ends
    slug = slug.strip('-')

    return f"https://www.udemy.com/course/{slug}/"
