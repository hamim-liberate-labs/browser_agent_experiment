"""Configuration settings for Udemy Agent.

All configuration is centralized here using Pydantic Settings for validation
and environment variable support.

Environment Variables:
    GROQ_API_KEY: API key for Groq LLM service (required)
    OPENAI_API_KEY: API key for OpenAI (optional)
    LLM_MODEL: Active model name (default: openai-gpt-oss-20b)
    BROWSER_HEADLESS: Run browser in headless mode
    LOG_LEVEL: Logging level
    LANGCHAIN_TRACING_V2: Enable LangSmith tracing
    LANGCHAIN_API_KEY: LangSmith API key
    LANGCHAIN_PROJECT: LangSmith project name
"""

import os
from pathlib import Path
from typing import Dict, Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class PathSettings(BaseSettings):
    """File and directory path settings."""

    base_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)

    @property
    def screenshot_dir(self) -> Path:
        """Screenshot directory path."""
        env_path = os.getenv("SCREENSHOT_DIR")
        if env_path:
            return Path(env_path)
        return self.base_dir / "screenshots"

    class Config:
        env_prefix = "LANGGRAPH_"


class ModelConfig(BaseSettings):
    """Configuration for a single LLM model."""

    base_url: str
    api_key_env: str
    model: str


# Available model configurations
MODEL_CONFIGS: Dict[str, Dict[str, str]] = {
    "openai-gpt-oss-20b": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "openai/gpt-oss-20b",
    },
    "groq-llama-3.3-70b": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
    },
    "groq-llama-3.1-8b": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "llama-3.1-8b-instant",
    },
    "openai-gpt-4o-mini": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
    },
}


class LLMSettings(BaseSettings):
    """LLM service configuration."""

    active_model: str = Field(default="openai-gpt-oss-20b")
    default_temperature: float = Field(default=0.1, ge=0.0, le=2.0)
    max_retries: int = Field(default=3, ge=1, le=10)

    class Config:
        env_prefix = "LLM_"

    def get_model_config(self, model_name: Optional[str] = None) -> Dict[str, str]:
        """Get configuration for specified model."""
        name = model_name or self.active_model
        if name not in MODEL_CONFIGS:
            raise ValueError(f"Unknown model '{name}'. Available: {list(MODEL_CONFIGS.keys())}")
        return MODEL_CONFIGS[name]

    def get_api_key(self, model_name: Optional[str] = None) -> str:
        """Get API key for specified model."""
        config = self.get_model_config(model_name)
        key = os.getenv(config["api_key_env"])
        if not key:
            raise ValueError(f"{config['api_key_env']} environment variable is required")
        return key


class BrowserSettings(BaseSettings):
    """Browser automation settings."""

    headless: bool = Field(default=True)
    viewport_width: int = Field(default=1920)
    viewport_height: int = Field(default=1080)
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        )
    )
    locale: str = Field(default="en-US")
    timezone: str = Field(default="America/New_York")
    cloudflare_max_wait: int = Field(default=30, ge=5, le=120)
    page_timeout: int = Field(default=30000, ge=5000, le=120000)

    class Config:
        env_prefix = "BROWSER_"


class TracingSettings(BaseSettings):
    """LangSmith tracing configuration."""

    enabled: bool = Field(default=False)
    api_key: Optional[str] = Field(default=None)
    project: str = Field(default="udemy-agent")

    class Config:
        env_prefix = "LANGCHAIN_"

    def __init__(self, **data):
        super().__init__(**data)
        # Check LANGCHAIN_TRACING_V2 environment variable
        if os.getenv("LANGCHAIN_TRACING_V2", "").lower() == "true":
            self.enabled = True
        if os.getenv("LANGCHAIN_API_KEY"):
            self.api_key = os.getenv("LANGCHAIN_API_KEY")
        if os.getenv("LANGCHAIN_PROJECT"):
            self.project = os.getenv("LANGCHAIN_PROJECT")


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
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    tracing: TracingSettings = Field(default_factory=TracingSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


# Global settings instance
settings = Settings()


# Convenience accessors
def get_paths() -> PathSettings:
    """Get path settings."""
    return settings.paths


def get_llm_settings() -> LLMSettings:
    """Get LLM settings."""
    return settings.llm


def get_browser_settings() -> BrowserSettings:
    """Get browser settings."""
    return settings.browser
