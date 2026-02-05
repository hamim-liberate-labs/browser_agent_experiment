"""State models for LangGraph workflows."""

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from udemy_agent.models.filters import BrowserFilters


# Valid intent types
IntentType = Literal[
    "trending", "top_rated", "new_courses", "search", "category",
    "course_details", "compare_courses", "complex_query", "chat"
]

# Chat agent status
ChatStatus = Literal["idle", "classifying", "browsing", "synthesizing", "responding", "done"]

# Browser agent status
BrowserStatus = Literal["continue", "done", "error"]


class UdemyChatState(BaseModel):
    """State for the Chat Agent (Supervisor)."""

    # Conversation
    messages: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Conversation history"
    )
    user_intent: Optional[IntentType] = Field(
        default=None,
        description="Classified user intent"
    )

    # Course details request
    target_course_url: Optional[str] = Field(
        default=None,
        description="Course URL for details request"
    )
    target_course_index: Optional[int] = Field(
        default=None,
        description="Course index from search results (1-based)"
    )

    # Course comparison
    compare_course_indices: Optional[List[int]] = Field(
        default=None,
        description="Indices of courses to compare"
    )
    compare_course_urls: Optional[List[str]] = Field(
        default=None,
        description="URLs of courses to compare"
    )
    comparison_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Comparison result data"
    )

    # Complex query
    complex_query_plan: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Execution plan for complex queries"
    )
    complex_query_results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Results from complex query execution"
    )

    # Screenshots
    capture_screenshots: bool = Field(
        default=False,
        description="Whether to capture screenshots"
    )
    screenshot_paths: Optional[Dict[str, str]] = Field(
        default=None,
        description="Paths to captured screenshots"
    )

    # Search results cache
    last_search_results: Optional[List[Dict[str, Any]]] = Field(
        default=None,
        description="Cached search results for follow-up queries"
    )

    # Browser delegation
    needs_browser: bool = Field(
        default=False,
        description="Whether request requires browser automation"
    )
    browser_task: Optional[str] = Field(
        default=None,
        description="Task description for browser agent"
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Search query extracted from message"
    )
    browser_filters: Optional[BrowserFilters] = Field(
        default=None,
        description="Filters to apply in browser"
    )
    browser_result: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Result from browser agent"
    )
    browser_page_content: Optional[str] = Field(
        default=None,
        description="Raw page content from browser"
    )

    # Status and response
    status: ChatStatus = Field(
        default="idle",
        description="Current workflow status"
    )
    response: Optional[str] = Field(
        default=None,
        description="Final response to user"
    )

    class Config:
        arbitrary_types_allowed = True


class UdemyBrowserState(BaseModel):
    """State for the Browser Agent (Worker)."""

    # Task
    objective: str = Field(
        default="",
        description="Task objective"
    )
    task_type: str = Field(
        default="trending",
        description="Type of task: trending, search, course_details, etc."
    )
    search_query: Optional[str] = Field(
        default=None,
        description="Search query if applicable"
    )
    course_detail_url: Optional[str] = Field(
        default=None,
        description="Course URL for detail extraction"
    )
    filters: Optional[BrowserFilters] = Field(
        default=None,
        description="Filters to apply"
    )

    # Browser state
    current_url: str = Field(
        default="",
        description="Current page URL"
    )
    page_text: str = Field(
        default="",
        description="Extracted page text"
    )
    page_type: str = Field(
        default="unknown",
        description="Type of page: homepage, topic, search, course_detail"
    )

    # Results
    extracted_courses: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Extracted course data"
    )
    course_urls: List[Dict[str, str]] = Field(
        default_factory=list,
        description="Extracted course URLs"
    )
    course_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Detailed course information"
    )

    # Status
    status: BrowserStatus = Field(
        default="continue",
        description="Current status"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error message if status is error"
    )

    class Config:
        arbitrary_types_allowed = True
