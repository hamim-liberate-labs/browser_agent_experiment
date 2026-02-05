"""Configuration settings for Udemy GPT.

All configuration is centralized here using Pydantic Settings for validation
and environment variable support.

Environment Variables:
    UDEMY_DATA_DIR: Path to data directory (default: ./udemy_data)
    GROQ_API_KEY: API key for Groq LLM service (required)
    LLM_BASE_URL: LLM API base URL
    LLM_MODEL: Model name to use (default: openai/gpt-oss-20b)
    LLM_MAX_RETRIES: Max retry attempts for LLM calls
    BROWSER_HEADLESS: Run browser in headless mode (true/false)
    LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR)
"""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class PathSettings(BaseSettings):
    """File and directory path settings."""

    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)

    @property
    def data_dir(self) -> Path:
        """Data directory path (can be overridden via UDEMY_DATA_DIR env var)."""
        env_path = os.getenv("UDEMY_DATA_DIR")
        if env_path:
            return Path(env_path)
        return self.base_dir / "udemy_data"

    @property
    def courses_dir(self) -> Path:
        """Directory containing course CSV files."""
        return self.data_dir / "courses"

    @property
    def topics_csv(self) -> Path:
        """Path to topics CSV file."""
        return self.data_dir / "udemy_topics_from_network.csv"

    class Config:
        env_prefix = "UDEMY_"


class LLMSettings(BaseSettings):
    """LLM service configuration."""

    base_url: str = Field(default="https://api.groq.com/openai/v1")
    api_key: Optional[str] = Field(default=None)
    model: str = Field(default="openai/gpt-oss-20b")
    max_retries: int = Field(default=3, ge=1, le=10)
    retry_delay: float = Field(default=1.0, ge=0.1)
    rate_limit_delay: float = Field(default=0.5, ge=0.0)
    default_temperature: float = Field(default=0.6, ge=0.0, le=2.0)

    class Config:
        env_prefix = "LLM_"

    def get_api_key(self) -> str:
        """Get API key from settings or environment."""
        key = self.api_key or os.getenv("GROQ_API_KEY")
        if not key:
            raise ValueError("GROQ_API_KEY environment variable is required")
        return key


class ConversationSettings(BaseSettings):
    """Conversation management settings."""

    max_history_messages: int = Field(default=10, ge=1, le=50)
    include_history_in_prompt: bool = Field(default=True)

    class Config:
        env_prefix = "CONVERSATION_"


class BrowserSettings(BaseSettings):
    """Browser automation settings for live course details."""

    headless: bool = Field(default=True)
    timeout: int = Field(default=30000, ge=5000, le=120000)
    cloudflare_wait: int = Field(default=20, ge=5, le=60)
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    )

    class Config:
        env_prefix = "BROWSER_"


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    class Config:
        env_prefix = "LOG_"


class Settings(BaseSettings):
    """Main settings container combining all configuration."""

    paths: PathSettings = Field(default_factory=PathSettings)
    llm: LLMSettings = Field(default_factory=LLMSettings)
    conversation: ConversationSettings = Field(default_factory=ConversationSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


# Global settings instance - import this in other modules
settings = Settings()


# Convenience accessors for backward compatibility
def get_paths() -> PathSettings:
    """Get path settings."""
    return settings.paths


def get_llm_settings() -> LLMSettings:
    """Get LLM settings."""
    return settings.llm


def get_browser_settings() -> BrowserSettings:
    """Get browser settings."""
    return settings.browser


def get_conversation_settings() -> ConversationSettings:
    """Get conversation settings."""
    return settings.conversation
