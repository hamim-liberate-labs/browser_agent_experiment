"""Configuration module for Udemy Agent."""

from udemy_agent.config.settings import (
    Settings,
    settings,
    get_paths,
    get_browser_settings,
    get_llm_settings,
)

__all__ = [
    "Settings",
    "settings",
    "get_paths",
    "get_browser_settings",
    "get_llm_settings",
]
