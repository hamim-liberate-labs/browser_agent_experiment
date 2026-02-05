"""Filter models for browser queries."""

from typing import Optional

from pydantic import BaseModel, Field


class BrowserFilters(BaseModel):
    """Filters to apply when browsing Udemy."""

    sort_by: Optional[str] = Field(
        default=None,
        description="Sort option: Most Popular, Highest Rated, Newest"
    )
    min_rating: Optional[str] = Field(
        default=None,
        description="Minimum rating filter: 4.5, 4.0, 3.5, 3.0"
    )
    duration: Optional[str] = Field(
        default=None,
        description="Duration filter: 0-1, 1-3, 3-6, 6-17, 17+"
    )
    level: Optional[str] = Field(
        default=None,
        description="Level filter: beginner, intermediate, expert, all"
    )
    price: Optional[str] = Field(
        default=None,
        description="Price filter: free, paid"
    )
    language: Optional[str] = Field(
        default=None,
        description="Language filter"
    )
    max_results: int = Field(
        default=20,
        description="Maximum number of courses to fetch"
    )

    def has_filters(self) -> bool:
        """Check if any filters are set."""
        return any([
            self.sort_by,
            self.min_rating,
            self.duration,
            self.level and self.level != "all",
            self.price,
            self.language,
        ])

    def describe(self) -> str:
        """Get human-readable filter description."""
        parts = []
        if self.sort_by:
            parts.append(f"Sorted by: {self.sort_by}")
        if self.min_rating:
            parts.append(f"Min rating: {self.min_rating}+")
        if self.duration:
            parts.append(f"Duration: {self.duration} hours")
        if self.level and self.level != "all":
            parts.append(f"Level: {self.level}")
        if self.price:
            parts.append(f"Price: {self.price}")
        if self.language:
            parts.append(f"Language: {self.language}")
        return ", ".join(parts) if parts else "None"
