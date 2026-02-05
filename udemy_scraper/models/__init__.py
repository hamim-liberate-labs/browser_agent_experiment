"""Data models for Udemy Scraper."""

from udemy_scraper.models.topic import Topic
from udemy_scraper.models.course import ScrapedCourse
from udemy_scraper.models.result import ScrapeResult, ScrapeSummary

__all__ = [
    "Topic",
    "ScrapedCourse",
    "ScrapeResult",
    "ScrapeSummary",
]
