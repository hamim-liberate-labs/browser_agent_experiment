"""Configuration settings for Udemy Scraper.

All configuration is centralized here using Pydantic Settings for validation
and environment variable support.

Environment Variables:
    UDEMY_DATA_DIR: Path to data directory (default: ./udemy_data)
    BROWSER_HEADLESS: Run browser in headless mode (true/false)
    BROWSER_TIMEOUT: Browser timeout in milliseconds
    SCRAPER_CLOUDFLARE_WAIT: Cloudflare challenge wait time
    SCRAPER_MIN_DELAY: Minimum delay between requests
    SCRAPER_MAX_DELAY: Maximum delay between requests
    SCRAPER_PAGES_PER_TOPIC: Number of pages to scrape per topic
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
    def topics_csv(self) -> Path:
        """Path to topics CSV file."""
        return self.data_dir / "udemy_topics_from_network.csv"

    @property
    def courses_dir(self) -> Path:
        """Directory for output course CSV files."""
        return self.data_dir / "courses"

    class Config:
        env_prefix = "UDEMY_"


class BrowserSettings(BaseSettings):
    """Browser automation settings."""

    headless: bool = Field(default=False)
    timeout: int = Field(default=30000, ge=5000, le=120000)
    user_agent: str = Field(
        default=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )
    )
    viewport_width: int = Field(default=1920, ge=800)
    viewport_height: int = Field(default=1080, ge=600)

    class Config:
        env_prefix = "BROWSER_"


class ScraperSettings(BaseSettings):
    """Scraper behavior settings."""

    cloudflare_wait: int = Field(default=30, ge=5, le=120)
    min_delay: float = Field(default=1.5, ge=0.5)
    max_delay: float = Field(default=2.5, ge=1.0)
    pages_per_topic: int = Field(default=2, ge=1, le=10)
    scroll_iterations: int = Field(default=5, ge=1, le=20)
    scroll_amount: int = Field(default=800, ge=100, le=2000)
    skip_existing: bool = Field(default=True)

    class Config:
        env_prefix = "SCRAPER_"


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: str = Field(default="INFO")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    class Config:
        env_prefix = "LOG_"


class Settings(BaseSettings):
    """Main settings container combining all configuration."""

    paths: PathSettings = Field(default_factory=PathSettings)
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    scraper: ScraperSettings = Field(default_factory=ScraperSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


# Global settings instance
settings = Settings()


# Convenience accessors
def get_paths() -> PathSettings:
    """Get path settings."""
    return settings.paths


def get_browser_settings() -> BrowserSettings:
    """Get browser settings."""
    return settings.browser


def get_scraper_settings() -> ScraperSettings:
    """Get scraper settings."""
    return settings.scraper
