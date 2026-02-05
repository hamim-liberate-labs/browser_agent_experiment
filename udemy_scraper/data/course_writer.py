"""Course writer for saving scraped data to CSV."""

import csv
from pathlib import Path
from typing import List

from udemy_scraper.config import get_paths
from udemy_scraper.exceptions import CourseWriteError
from udemy_scraper.models import ScrapedCourse, Topic


class CourseWriter:
    """Writes scraped courses to CSV files."""

    def __init__(self, output_dir: Path = None):
        self._output_dir = output_dir or get_paths().courses_dir

    @property
    def output_dir(self) -> Path:
        """Get output directory."""
        return self._output_dir

    def get_output_path(self, topic: Topic) -> Path:
        """Get output CSV path for a topic.

        Args:
            topic: Topic to get path for

        Returns:
            Path to output CSV file
        """
        return self._output_dir / topic.safe_section / f"{topic.slug}.csv"

    def exists(self, topic: Topic) -> bool:
        """Check if output file already exists.

        Args:
            topic: Topic to check

        Returns:
            True if output file exists
        """
        return self.get_output_path(topic).exists()

    def save(self, courses: List[ScrapedCourse], topic: Topic) -> Path:
        """Save courses to CSV file.

        Args:
            courses: List of courses to save
            topic: Topic these courses belong to

        Returns:
            Path to saved file

        Raises:
            CourseWriteError: If save fails
        """
        if not courses:
            return None

        output_path = self.get_output_path(topic)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            columns = ScrapedCourse.csv_columns()

            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=columns, extrasaction='ignore')
                writer.writeheader()
                for course in courses:
                    writer.writerow(course.to_dict())

            return output_path

        except Exception as e:
            raise CourseWriteError(f"Failed to save courses: {e}")

    def ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        self._output_dir.mkdir(parents=True, exist_ok=True)
