"""Result models for scraping operations."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from udemy_scraper.models.course import ScrapedCourse


@dataclass
class ScrapeResult:
    """Result of scraping a single topic."""

    topic_name: str
    topic_slug: str
    courses: List[ScrapedCourse] = field(default_factory=list)
    success: bool = False
    error: Optional[str] = None
    output_path: Optional[Path] = None

    @property
    def course_count(self) -> int:
        """Number of courses scraped."""
        return len(self.courses)


@dataclass
class ScrapeSummary:
    """Summary of full scraping session."""

    total_topics: int = 0
    successful_topics: int = 0
    failed_topics: List[str] = field(default_factory=list)
    skipped_topics: List[str] = field(default_factory=list)
    total_courses: int = 0
    output_dir: Optional[Path] = None

    @property
    def failure_count(self) -> int:
        """Number of failed topics."""
        return len(self.failed_topics)

    @property
    def skipped_count(self) -> int:
        """Number of skipped topics."""
        return len(self.skipped_topics)

    def add_result(self, result: ScrapeResult):
        """Add a scrape result to summary."""
        if result.success:
            self.successful_topics += 1
            self.total_courses += result.course_count
        else:
            self.failed_topics.append(result.topic_name)

    def add_skipped(self, topic_name: str):
        """Add a skipped topic to summary."""
        self.skipped_topics.append(topic_name)

    def format_summary(self) -> str:
        """Format summary as string."""
        lines = [
            "=" * 60,
            "SCRAPING COMPLETE",
            "=" * 60,
            f"Total topics: {self.total_topics}",
            f"Successful: {self.successful_topics}",
            f"Skipped: {self.skipped_count}",
            f"Failed: {self.failure_count}",
            f"Total courses: {self.total_courses}",
            f"Output: {self.output_dir}",
            "=" * 60,
        ]

        if self.failed_topics:
            lines.append(f"\nFailed topics ({self.failure_count}):")
            for topic in self.failed_topics[:10]:
                lines.append(f"  - {topic}")
            if self.failure_count > 10:
                lines.append(f"  ... and {self.failure_count - 10} more")

        return "\n".join(lines)
