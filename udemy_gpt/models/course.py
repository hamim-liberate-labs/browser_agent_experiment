"""Course-related data models."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


@dataclass
class Course:
    """Basic course information from knowledge base."""

    title: str
    url: str = ""
    instructor: str = ""
    rating: float = 0.0
    reviews_count: int = 0
    price: str = ""
    original_price: str = ""
    duration: str = ""
    lectures: str = ""
    level: str = ""
    bestseller: bool = False
    topic: str = ""
    section: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "url": self.url,
            "instructor": self.instructor,
            "rating": self.rating,
            "reviews_count": self.reviews_count,
            "price": self.price,
            "original_price": self.original_price,
            "duration": self.duration,
            "lectures": self.lectures,
            "level": self.level,
            "bestseller": self.bestseller,
            "topic": self.topic,
            "section": self.section,
        }


@dataclass
class TopicStats:
    """Statistics for a topic."""

    topic: str
    course_count: int = 0
    avg_rating: float = 0.0
    avg_price: float = 0.0
    total_reviews: int = 0
    free_courses: int = 0
    beginner_courses: int = 0
    top_course: Optional[Course] = None


@dataclass
class TopicComparison:
    """Comparison results between multiple topics."""

    topics: Dict[str, TopicStats] = field(default_factory=dict)
    recommendation: str = ""


class CourseDetails(BaseModel):
    """Detailed course information fetched from Udemy via browser."""

    title: str = ""
    subtitle: str = ""
    description: str = ""
    url: str = ""
    rating: str = ""
    reviews_count: str = ""
    students: str = ""
    last_updated: str = ""
    language: str = ""
    level: str = ""
    price: str = ""
    original_price: str = ""
    duration: str = ""
    lectures: str = ""
    sections: str = ""
    articles: str = ""
    resources: str = ""
    curriculum: List[Dict[str, Any]] = Field(default_factory=list)
    instructor_name: str = ""
    instructor_title: str = ""
    instructor_rating: str = ""
    instructor_students: str = ""
    instructor_courses: str = ""
    requirements: List[str] = Field(default_factory=list)
    objectives: List[str] = Field(default_factory=list)
    target_audience: List[str] = Field(default_factory=list)
    reviews: List[Dict[str, str]] = Field(default_factory=list)
