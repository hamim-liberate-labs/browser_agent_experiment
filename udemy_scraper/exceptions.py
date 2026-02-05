"""Custom exceptions for Udemy Scraper."""


class ScraperError(Exception):
    """Base exception for all scraper errors."""

    pass


class BrowserError(ScraperError):
    """Browser automation errors."""

    pass


class CloudflareBlockedError(BrowserError):
    """Cloudflare challenge could not be bypassed."""

    pass


class NavigationError(BrowserError):
    """Page navigation failed."""

    pass


class DataError(ScraperError):
    """Data loading or saving errors."""

    pass


class TopicLoadError(DataError):
    """Failed to load topics from CSV."""

    pass


class CourseWriteError(DataError):
    """Failed to write courses to CSV."""

    pass


class ExtractionError(ScraperError):
    """Course data extraction failed."""

    pass
