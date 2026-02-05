"""Intent handlers for Udemy GPT.

Each handler is responsible for processing a specific type of user intent
and generating appropriate responses.
"""

from udemy_gpt.core.handlers.search import SearchHandler
from udemy_gpt.core.handlers.compare import CompareHandler
from udemy_gpt.core.handlers.details import DetailsHandler
from udemy_gpt.core.handlers.learning_path import LearningPathHandler
from udemy_gpt.core.handlers.chat import ChatHandler

__all__ = [
    "SearchHandler",
    "CompareHandler",
    "DetailsHandler",
    "LearningPathHandler",
    "ChatHandler",
]
