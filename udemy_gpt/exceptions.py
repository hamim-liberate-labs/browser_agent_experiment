"""Custom exceptions for Udemy GPT.

This module defines a hierarchy of exceptions for handling
different error conditions in the application.
"""


class UdemyGPTError(Exception):
    """Base exception for all Udemy GPT errors."""

    pass


class ConfigurationError(UdemyGPTError):
    """Raised when configuration is invalid or missing."""

    pass


class LLMError(UdemyGPTError):
    """Raised when LLM operations fail."""

    pass


class BrowserError(UdemyGPTError):
    """Raised when browser automation fails."""

    pass


class DataError(UdemyGPTError):
    """Raised when data operations fail."""

    pass


class TopicNotFoundError(DataError):
    """Raised when a requested topic is not found."""

    def __init__(self, topic: str):
        self.topic = topic
        super().__init__(f"Topic not found: {topic}")


class CourseNotFoundError(DataError):
    """Raised when a requested course is not found."""

    def __init__(self, course_id: str):
        self.course_id = course_id
        super().__init__(f"Course not found: {course_id}")


class IntentClassificationError(UdemyGPTError):
    """Raised when intent classification fails."""

    pass
