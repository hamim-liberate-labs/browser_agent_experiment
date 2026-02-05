"""Topic model for scraper input."""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Topic:
    """Represents a Udemy topic to scrape."""

    name: str
    slug: str
    url: str
    section: str = "Other"

    @classmethod
    def from_dict(cls, data: dict) -> "Topic":
        """Create Topic from CSV row dictionary."""
        return cls(
            name=data.get("name", "Unknown"),
            slug=data.get("slug", "unknown"),
            url=data.get("url", ""),
            section=data.get("section", "Other"),
        )

    @property
    def safe_section(self) -> str:
        """Get filesystem-safe section name."""
        return re.sub(r'[<>:"/\\|?*]', '_', self.section)[:100]

    @property
    def is_valid(self) -> bool:
        """Check if topic has required fields."""
        return bool(self.url and self.slug)
