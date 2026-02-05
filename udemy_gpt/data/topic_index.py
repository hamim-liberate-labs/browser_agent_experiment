"""Topic index management for course discovery.

This module handles topic indexing, validation, fuzzy matching,
and provides the topic catalog for the LLM.
"""

import csv
import logging
from difflib import SequenceMatcher
from typing import Dict, List, Optional, Set

from udemy_gpt.config import settings

logger = logging.getLogger(__name__)

# Module-level cache
_topic_index: Optional[Dict[str, Dict]] = None
_topic_list_for_llm: str = ""
_topic_aliases: Dict[str, str] = {}


# =============================================================================
# Topic Aliases
# =============================================================================

def _build_topic_aliases(index: Dict[str, Dict]) -> Dict[str, str]:
    """Build common aliases for fuzzy topic matching.

    Args:
        index: Topic index dictionary

    Returns:
        Mapping of aliases to canonical topic slugs
    """
    # Common abbreviations and alternate names
    aliases = {
        "ml": "machine-learning",
        "ai": "artificial-intelligence",
        "dl": "deep-learning",
        "ds": "data-science",
        "js": "javascript",
        "ts": "typescript",
        "py": "python",
        "cpp": "c++",
        "csharp": "c#",
        "k8s": "kubernetes",
        "aws": "amazon-web-services",
        "gcp": "google-cloud",
        "nlp": "natural-language-processing",
        "cv": "computer-vision",
        "reactjs": "react",
        "nodejs": "nodejs",
        "vuejs": "vue",
    }

    # Filter to only valid targets that have courses
    valid_aliases = {}
    for alias, target in aliases.items():
        if target in index and index[target].get("course_count", 0) > 0:
            valid_aliases[alias] = target

    # Add self-references for all valid topics (without hyphens, with spaces)
    for slug in index:
        if index[slug].get("course_count", 0) > 0:
            no_hyphen = slug.replace("-", "")
            if no_hyphen != slug:
                valid_aliases[no_hyphen] = slug
            with_space = slug.replace("-", " ")
            if with_space != slug:
                valid_aliases[with_space] = slug

    return valid_aliases


# =============================================================================
# Index Building
# =============================================================================

def build_index() -> Dict[str, Dict]:
    """Build index of available topics from CSV files.

    Scans the courses directory and builds a comprehensive index
    of all available topics with their metadata.

    Returns:
        Topic index dictionary
    """
    global _topic_index, _topic_list_for_llm, _topic_aliases

    if _topic_index is not None:
        return _topic_index

    logger.info("Building topic index...")
    index = {}
    paths = settings.paths

    # Scan courses directory
    if paths.courses_dir.exists():
        for section_dir in paths.courses_dir.iterdir():
            if section_dir.is_dir():
                section = section_dir.name
                for csv_file in section_dir.glob("*.csv"):
                    slug = csv_file.stem
                    try:
                        with open(csv_file, "r", encoding="utf-8") as f:
                            reader = csv.DictReader(f)
                            course_count = sum(1 for _ in reader)
                    except Exception as e:
                        logger.warning(f"Error counting courses in {csv_file}: {e}")
                        course_count = 0

                    index[slug] = {
                        "path": str(csv_file.relative_to(paths.courses_dir)),
                        "full_path": str(csv_file),
                        "section": section,
                        "course_count": course_count,
                    }

    # Also index from topics CSV for reference
    if paths.topics_csv.exists():
        try:
            with open(paths.topics_csv, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    slug = row.get("slug", "")
                    if slug and slug not in index:
                        index[slug] = {
                            "name": row.get("name", slug),
                            "url": row.get("url", ""),
                            "section": row.get("section", ""),
                            "course_count": 0,
                        }
        except Exception as e:
            logger.warning(f"Error reading topics CSV: {e}")

    _topic_index = index
    _topic_aliases = _build_topic_aliases(index)

    # Build formatted list for LLM context
    available_topics = [
        f"- {slug} ({info['course_count']} courses, {info['section']})"
        for slug, info in index.items()
        if info.get("course_count", 0) > 0
    ]
    _topic_list_for_llm = "\n".join(sorted(available_topics))

    topics_with_courses = len([t for t in index.values() if t.get("course_count", 0) > 0])
    logger.info(f"Index built: {topics_with_courses} topics with courses")

    return index


def get_index() -> Dict[str, Dict]:
    """Get the topic index, building if necessary.

    Returns:
        Topic index dictionary
    """
    if _topic_index is None:
        build_index()
    return _topic_index


def get_topic_list_for_llm() -> str:
    """Get pre-formatted topic list for LLM context.

    Returns:
        Formatted string listing all available topics
    """
    if not _topic_list_for_llm:
        build_index()
    return _topic_list_for_llm


# =============================================================================
# Topic Queries
# =============================================================================

def get_available_slugs() -> Set[str]:
    """Get set of all available topic slugs with courses.

    Returns:
        Set of topic slug strings
    """
    index = get_index()
    return {slug for slug, info in index.items() if info.get("course_count", 0) > 0}


def get_available_topics() -> List[Dict]:
    """Get list of available topics with metadata.

    Returns:
        List of topic dictionaries sorted by course count
    """
    index = get_index()
    topics = []
    for slug, info in index.items():
        if info.get("course_count", 0) > 0:
            topics.append({
                "slug": slug,
                "section": info.get("section", ""),
                "course_count": info.get("course_count", 0),
            })
    return sorted(topics, key=lambda x: x["course_count"], reverse=True)


def search_topics(query: str) -> List[str]:
    """Search for matching topic slugs.

    Args:
        query: Search query string

    Returns:
        List of matching topic slugs
    """
    index = get_index()
    query_lower = query.lower().replace(" ", "-").replace("_", "-")

    matches = []
    for slug, info in index.items():
        if slug == query_lower:
            matches.insert(0, slug)
        elif query_lower in slug or slug in query_lower:
            matches.append(slug)
        elif "name" in info and query.lower() in info["name"].lower():
            matches.append(slug)

    return matches


# =============================================================================
# Topic Validation
# =============================================================================

def _fuzzy_match_topic(query: str, index: Dict[str, Dict], threshold: float = 0.7) -> Optional[str]:
    """Find best fuzzy match for a topic query.

    Args:
        query: Topic query string
        index: Topic index
        threshold: Minimum similarity threshold

    Returns:
        Best matching topic slug or None
    """
    best_match = None
    best_score = 0
    query_normalized = query.replace("-", "").replace("_", "").replace(" ", "").lower()

    for slug, info in index.items():
        if info.get("course_count", 0) == 0:
            continue
        slug_normalized = slug.replace("-", "").replace("_", "").replace(" ", "").lower()

        # Check if query is substring
        if query_normalized in slug_normalized or slug_normalized in query_normalized:
            score = 0.8 + (len(query_normalized) / len(slug_normalized)) * 0.2
            if score > best_score:
                best_score = score
                best_match = slug
            continue

        # Use sequence matcher for similarity
        score = SequenceMatcher(None, query_normalized, slug_normalized).ratio()
        if score > best_score and score >= threshold:
            best_score = score
            best_match = slug

    return best_match


def validate_topics(topics: List[str]) -> List[str]:
    """Validate and normalize topic slugs with fuzzy matching.

    Args:
        topics: List of topic strings to validate

    Returns:
        List of valid, normalized topic slugs
    """
    global _topic_aliases
    index = get_index()

    if not _topic_aliases:
        build_index()

    validated = []
    seen = set()

    for topic in topics:
        if not topic:
            continue
        normalized = topic.lower().strip()

        # Check direct match
        if normalized in index and index[normalized].get("course_count", 0) > 0:
            if normalized not in seen:
                validated.append(normalized)
                seen.add(normalized)
            continue

        # Check aliases
        if normalized in _topic_aliases:
            target = _topic_aliases[normalized]
            if target not in seen:
                validated.append(target)
                seen.add(target)
            continue

        # Try fuzzy match
        fuzzy_match = _fuzzy_match_topic(normalized, index)
        if fuzzy_match and fuzzy_match not in seen:
            validated.append(fuzzy_match)
            seen.add(fuzzy_match)

    return validated


def reset_index() -> None:
    """Reset the topic index (for testing or reloading)."""
    global _topic_index, _topic_list_for_llm, _topic_aliases
    _topic_index = None
    _topic_list_for_llm = ""
    _topic_aliases = {}
    logger.info("Topic index reset")
