"""Course model for scraped data."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ScrapedCourse:
    """Represents a scraped course from Udemy."""

    title: str
    url: Optional[str] = None
    instructor: Optional[str] = None
    rating: Optional[str] = None
    reviews_count: Optional[str] = None
    price: Optional[str] = None
    original_price: Optional[str] = None
    duration: Optional[str] = None
    lectures: Optional[str] = None
    level: Optional[str] = None
    bestseller: bool = False

    @classmethod
    def from_dict(cls, data: dict) -> "ScrapedCourse":
        """Create ScrapedCourse from extracted dictionary."""
        return cls(
            title=data.get("title", ""),
            url=data.get("url"),
            instructor=data.get("instructor"),
            rating=data.get("rating"),
            reviews_count=data.get("reviews_count"),
            price=data.get("price"),
            original_price=data.get("original_price"),
            duration=data.get("duration"),
            lectures=data.get("lectures"),
            level=data.get("level"),
            bestseller=bool(data.get("bestseller")),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for CSV output."""
        return {
            "title": self.title,
            "url": self.url or "",
            "instructor": self.instructor or "",
            "rating": self.rating or "",
            "reviews_count": self.reviews_count or "",
            "price": self.price or "",
            "original_price": self.original_price or "",
            "duration": self.duration or "",
            "lectures": self.lectures or "",
            "level": self.level or "",
            "bestseller": str(self.bestseller).lower(),
        }

    @property
    def is_valid(self) -> bool:
        """Check if course has required data."""
        return bool(self.title)

    @staticmethod
    def csv_columns() -> list:
        """Get CSV column names."""
        return [
            "title", "url", "instructor", "rating", "reviews_count",
            "price", "original_price", "duration", "lectures", "level", "bestseller"
        ]
