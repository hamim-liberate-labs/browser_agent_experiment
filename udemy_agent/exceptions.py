"""Custom exceptions for Udemy Agent."""


class AgentError(Exception):
    """Base exception for all agent errors."""

    pass


class LLMError(AgentError):
    """LLM service errors."""

    pass


class BrowserError(AgentError):
    """Browser automation errors."""

    pass


class CloudflareBlockedError(BrowserError):
    """Cloudflare challenge could not be bypassed."""

    pass


class PageLoadError(BrowserError):
    """Page navigation failed."""

    pass


class ExtractionError(AgentError):
    """Content extraction failed."""

    pass


class WorkflowError(AgentError):
    """LangGraph workflow execution error."""

    pass


class ConfigurationError(AgentError):
    """Configuration or environment error."""

    pass
