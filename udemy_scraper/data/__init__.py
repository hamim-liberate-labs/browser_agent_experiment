"""Data access layer for Udemy Scraper."""

from udemy_scraper.data.topic_repository import TopicRepository
from udemy_scraper.data.course_writer import CourseWriter

__all__ = [
    "TopicRepository",
    "CourseWriter",
]
