"""Conversation state management models."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ConversationState(BaseModel):
    """State for managing conversation context.

    Tracks message history, search results, and current context
    to enable multi-turn conversations with context awareness.

    Attributes:
        messages: List of conversation messages with role and content
        last_search_results: Courses from most recent search
        last_topic: Most recently searched topic
        last_query: Most recent user query
        current_intent: Currently active intent type
        extracted_topics: Topics extracted in current session
        extracted_filters: Filters extracted in current session
        referenced_course_index: Course index user is asking about
    """

    messages: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Conversation history [{role: 'user'|'assistant', content: str}]",
    )
    last_search_results: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Courses from most recent search",
    )
    last_topic: Optional[str] = Field(
        default=None,
        description="Most recently searched topic slug",
    )
    last_query: Optional[str] = Field(
        default=None,
        description="Most recent user query",
    )
    current_intent: Optional[str] = Field(
        default=None,
        description="Currently active intent type",
    )
    extracted_topics: List[str] = Field(
        default_factory=list,
        description="Topics extracted in current session",
    )
    extracted_filters: Dict[str, Any] = Field(
        default_factory=dict,
        description="Filters extracted in current session",
    )
    referenced_course_index: Optional[int] = Field(
        default=None,
        description="1-based course index user is asking about",
    )

    class Config:
        arbitrary_types_allowed = True

    def add_message(self, role: str, content: str) -> None:
        """Add a message to conversation history."""
        self.messages.append({"role": role, "content": content})

    def clear(self) -> None:
        """Clear all state."""
        self.messages.clear()
        self.last_search_results.clear()
        self.last_topic = None
        self.last_query = None
        self.current_intent = None
        self.extracted_topics.clear()
        self.extracted_filters.clear()
        self.referenced_course_index = None

    def trim_history(self, max_messages: int) -> None:
        """Trim message history to max_messages."""
        if len(self.messages) > max_messages:
            self.messages = self.messages[-max_messages:]
