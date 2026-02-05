"""Udemy GPT - AI-powered course discovery assistant.

A conversational assistant that helps users discover, compare,
and choose Udemy courses using natural language queries.

Quick Start:
    ```python
    from udemy_gpt import UdemyGPT

    agent = UdemyGPT()
    response = await agent.chat("Find Python courses for beginners")
    print(response)
    await agent.close()
    ```

CLI Usage:
    ```bash
    python -m udemy_gpt
    ```
"""

__version__ = "1.0.0"

# Core
from udemy_gpt.core import UdemyGPT

# Models
from udemy_gpt.models import (
    Course,
    TopicStats,
    TopicComparison,
    CourseDetails,
    IntentClassification,
    ConversationState,
)

# Configuration
from udemy_gpt.config import settings

# Exceptions
from udemy_gpt.exceptions import (
    UdemyGPTError,
    ConfigurationError,
    LLMError,
    BrowserError,
    DataError,
    TopicNotFoundError,
    CourseNotFoundError,
    IntentClassificationError,
)

__all__ = [
    # Version
    "__version__",
    # Core
    "UdemyGPT",
    # Models
    "Course",
    "TopicStats",
    "TopicComparison",
    "CourseDetails",
    "IntentClassification",
    "ConversationState",
    # Config
    "settings",
    # Exceptions
    "UdemyGPTError",
    "ConfigurationError",
    "LLMError",
    "BrowserError",
    "DataError",
    "TopicNotFoundError",
    "CourseNotFoundError",
    "IntentClassificationError",
]
