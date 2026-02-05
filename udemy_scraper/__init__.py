"""Udemy Course Scraper - Scrapes course data from Udemy to CSV files.

This module provides tools for scraping Udemy course listings and saving
them to CSV files organized by topic.

Usage:
    # CLI
    python -m udemy_scraper
    udemy-scraper

    # Programmatic
    from udemy_scraper import UdemyScraper
    scraper = UdemyScraper()
    await scraper.run()
"""

from udemy_scraper.core import UdemyScraper
from udemy_scraper.config import settings
from udemy_scraper.exceptions import (
    ScraperError,
    BrowserError,
    DataError,
)
from udemy_scraper.models import (
    Topic,
    ScrapedCourse,
    ScrapeResult,
    ScrapeSummary,
)

__version__ = "1.0.0"
__all__ = [
    # Main
    "UdemyScraper",
    "settings",
    # Exceptions
    "ScraperError",
    "BrowserError",
    "DataError",
    # Models
    "Topic",
    "ScrapedCourse",
    "ScrapeResult",
    "ScrapeSummary",
]
