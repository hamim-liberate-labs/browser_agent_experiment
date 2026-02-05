"""Knowledge base for Udemy navigation patterns and selectors."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


# Popular topics with their URL slugs
POPULAR_TOPICS: Dict[str, str] = {
    "python": "python",
    "javascript": "javascript",
    "java": "java",
    "react": "react-js",
    "angular": "angular",
    "nodejs": "node-js",
    "web development": "web-development",
    "data science": "data-science",
    "machine learning": "machine-learning",
    "deep learning": "deep-learning",
    "artificial intelligence": "artificial-intelligence",
    "aws": "amazon-aws",
    "azure": "microsoft-azure",
    "docker": "docker",
    "kubernetes": "kubernetes",
    "sql": "sql",
    "excel": "excel",
    "power bi": "power-bi",
    "tableau": "tableau",
    "flutter": "flutter",
    "android": "android-development",
    "ios": "ios-development",
    "swift": "swift",
    "kotlin": "kotlin",
    "c++": "c-plus-plus",
    "c#": "c-sharp",
    "go": "go-programming-language",
    "rust": "rust-programming-language",
    "typescript": "typescript",
    "vue": "vue-js",
    "django": "django",
    "flask": "flask",
    "fastapi": "fastapi",
    "tensorflow": "tensorflow",
    "pytorch": "pytorch",
    "nlp": "natural-language-processing",
}

# Category mappings
CATEGORIES: Dict[str, str] = {
    "development": "development",
    "business": "business",
    "it": "it-software",
    "design": "design",
    "marketing": "marketing",
    "personal development": "personal-development",
    "music": "music",
    "photography": "photography-and-video",
}


@dataclass
class UdemyKnowledge:
    """Udemy platform knowledge."""

    popular_topics: Dict[str, str] = field(default_factory=lambda: POPULAR_TOPICS)
    categories: Dict[str, str] = field(default_factory=lambda: CATEGORIES)
    base_url: str = "https://www.udemy.com"


UDEMY_KNOWLEDGE = UdemyKnowledge()


def normalize_topic_name(topic: str) -> str:
    """Normalize topic name for URL.

    Args:
        topic: Topic name from user query

    Returns:
        URL-safe topic slug
    """
    topic_lower = topic.lower().strip()

    # Check direct match
    if topic_lower in POPULAR_TOPICS:
        return POPULAR_TOPICS[topic_lower]

    # Try partial match
    for name, slug in POPULAR_TOPICS.items():
        if topic_lower in name or name in topic_lower:
            return slug

    # Default: convert to URL slug
    return topic_lower.replace(" ", "-").replace("_", "-")


def get_topic_url(topic: str) -> str:
    """Get Udemy URL for a topic.

    Args:
        topic: Topic name

    Returns:
        Full Udemy topic URL
    """
    slug = normalize_topic_name(topic)
    return f"https://www.udemy.com/topic/{slug}/"


def get_search_url(query: str, sort: Optional[str] = None) -> str:
    """Get Udemy search URL.

    Args:
        query: Search query
        sort: Sort option (optional)

    Returns:
        Full Udemy search URL
    """
    query_encoded = query.replace(" ", "+")
    url = f"https://www.udemy.com/courses/search/?q={query_encoded}"

    if sort:
        sort_map = {
            "highest rated": "highest-rated",
            "newest": "newest",
            "most popular": "popularity",
            "most relevant": "relevance",
        }
        sort_param = sort_map.get(sort.lower(), sort.lower().replace(" ", "-"))
        url += f"&sort={sort_param}"

    return url


def get_action_for_intent(intent: str, search_query: Optional[str] = None) -> Dict[str, Any]:
    """Get navigation action based on intent.

    Args:
        intent: User intent type
        search_query: Search query if applicable

    Returns:
        Dictionary with URL, page_type, sort_by, action, wait_time
    """
    if intent == "trending":
        return {
            "url": "https://www.udemy.com/",
            "page_type": "homepage",
            "sort_by": "Most Popular",
            "action": "change_sort",
            "wait_time": 5000,
        }

    elif intent == "top_rated":
        if search_query:
            return {
                "url": get_search_url(search_query, "highest rated"),
                "page_type": "search",
                "sort_by": "Highest Rated",
                "action": None,
                "wait_time": 5000,
            }
        return {
            "url": "https://www.udemy.com/courses/development/?sort=highest-rated",
            "page_type": "category",
            "sort_by": "Highest Rated",
            "action": None,
            "wait_time": 5000,
        }

    elif intent == "new_courses":
        if search_query:
            return {
                "url": get_search_url(search_query, "newest"),
                "page_type": "search",
                "sort_by": "Newest",
                "action": None,
                "wait_time": 5000,
            }
        return {
            "url": "https://www.udemy.com/courses/development/?sort=newest",
            "page_type": "category",
            "sort_by": "Newest",
            "action": None,
            "wait_time": 5000,
        }

    elif intent == "search" and search_query:
        return {
            "url": get_topic_url(search_query),
            "page_type": "topic",
            "sort_by": None,
            "action": None,
            "wait_time": 5000,
        }

    elif intent == "category" and search_query:
        category_slug = CATEGORIES.get(search_query.lower(), search_query.lower())
        return {
            "url": f"https://www.udemy.com/courses/{category_slug}/",
            "page_type": "category",
            "sort_by": None,
            "action": None,
            "wait_time": 5000,
        }

    else:
        return {
            "url": "https://www.udemy.com/",
            "page_type": "homepage",
            "sort_by": None,
            "action": None,
            "wait_time": 5000,
        }


# Natural browsing patterns
BROWSING_PATTERNS: Dict[str, Any] = {
    "natural_delays": {
        "between_pages": (2.0, 4.0),
        "after_page_load": (1.5, 3.0),
        "after_scroll": (0.5, 1.0),
        "after_click": (0.8, 1.5),
    },
    "session_establishment": {
        "homepage_wait": 3000,
        "cookie_accept_wait": 1000,
    },
}

# Filter selectors for Udemy pages
FILTER_SELECTORS: Dict[str, Dict[str, Any]] = {
    "sort_dropdown": {
        "trigger": [
            '[data-purpose="sort-dropdown"]',
            'button[data-purpose="open-popup-sort"]',
            '.filter-panel--sort--button',
            'button:has-text("Sort by")',
        ],
        "options": {
            "Most Popular": ['text="Most Popular"', 'button:has-text("Most Popular")'],
            "Highest Rated": ['text="Highest Rated"', 'button:has-text("Highest Rated")'],
            "Newest": ['text="Newest"', 'button:has-text("Newest")'],
            "Most Relevant": ['text="Most Relevant"', 'button:has-text("Most Relevant")'],
        },
    },
    "rating_filter": {
        "trigger": [
            '[data-purpose="rating-filter"]',
            'button:has-text("Rating")',
            '.filter-panel--ratings',
        ],
        "options": {
            "4.5": ['text="4.5 & up"', 'input[value="4.5"]'],
            "4.0": ['text="4.0 & up"', 'input[value="4.0"]'],
            "3.5": ['text="3.5 & up"', 'input[value="3.5"]'],
            "3.0": ['text="3.0 & up"', 'input[value="3.0"]'],
        },
    },
    "duration_filter": {
        "trigger": [
            '[data-purpose="duration-filter"]',
            'button:has-text("Duration")',
            '.filter-panel--duration',
        ],
        "options": {
            "0-1": ['text="0-1 Hour"', 'input[value="extraShort"]'],
            "1-3": ['text="1-3 Hours"', 'input[value="short"]'],
            "3-6": ['text="3-6 Hours"', 'input[value="medium"]'],
            "6-17": ['text="6-17 Hours"', 'input[value="long"]'],
            "17+": ['text="17+ Hours"', 'input[value="extraLong"]'],
        },
    },
    "level_filter": {
        "trigger": [
            '[data-purpose="level-filter"]',
            'button:has-text("Level")',
            '.filter-panel--level',
        ],
        "options": {
            "beginner": ['text="Beginner"', 'input[value="beginner"]'],
            "intermediate": ['text="Intermediate"', 'input[value="intermediate"]'],
            "expert": ['text="Expert"', 'input[value="expert"]'],
            "all": ['text="All Levels"', 'input[value="all"]'],
        },
    },
    "price_filter": {
        "trigger": [
            '[data-purpose="price-filter"]',
            'button:has-text("Price")',
            '.filter-panel--price',
        ],
        "options": {
            "free": ['text="Free"', 'input[value="free"]'],
            "paid": ['text="Paid"', 'input[value="paid"]'],
        },
    },
    "pagination": {
        "load_more": [
            'button:has-text("Show more")',
            '[data-purpose="show-more-courses"]',
            '.pagination--show-more',
        ],
    },
}
