"""Intent classification models."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# Supported intent types
IntentType = Literal[
    "search",
    "recommend",
    "compare",
    "compare_topics",
    "details",
    "filter",
    "stats",
    "top_valuable",
    "cross_topic_analysis",
    "learning_path",
    "chat",
]


class IntentClassification(BaseModel):
    """Result of intent classification from user query.

    Attributes:
        intent: The classified intent type
        topics: List of topic slugs extracted from query
        filters: Search filters (rating, price, duration, etc.)
        course_reference: Course index if user refers to a specific course
        needs_browser: Whether live browser fetch is needed
        goal: Career or learning goal for learning path intent
    """

    intent: IntentType = Field(
        default="chat",
        description="Classified intent type",
    )
    topics: List[str] = Field(
        default_factory=list,
        description="Topic slugs extracted from query",
    )
    filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Search filters (min_rating, max_price, level, etc.)",
    )
    course_reference: Optional[int] = Field(
        default=None,
        description="1-based course index if referencing previous results",
    )
    needs_browser: bool = Field(
        default=False,
        description="Whether to fetch live data from Udemy",
    )
    goal: Optional[str] = Field(
        default=None,
        description="Career or learning goal for learning path",
    )
