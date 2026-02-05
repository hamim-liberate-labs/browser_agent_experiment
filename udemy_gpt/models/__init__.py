"""Data models for Udemy GPT."""

from udemy_gpt.models.course import (
    Course,
    TopicStats,
    TopicComparison,
    CourseDetails,
)
from udemy_gpt.models.intent import (
    IntentType,
    IntentClassification,
)
from udemy_gpt.models.state import ConversationState

__all__ = [
    # Course models
    "Course",
    "TopicStats",
    "TopicComparison",
    "CourseDetails",
    # Intent models
    "IntentType",
    "IntentClassification",
    # State models
    "ConversationState",
]
