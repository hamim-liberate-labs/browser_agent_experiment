"""Topic repository for loading input topics."""

import csv
from pathlib import Path
from typing import List

from udemy_scraper.config import get_paths
from udemy_scraper.exceptions import TopicLoadError
from udemy_scraper.models import Topic


class TopicRepository:
    """Loads topics from CSV input file."""

    def __init__(self, topics_csv: Path = None):
        self._topics_csv = topics_csv or get_paths().topics_csv
        self._topics: List[Topic] = []

    @property
    def topics_csv(self) -> Path:
        """Get topics CSV path."""
        return self._topics_csv

    def load(self) -> List[Topic]:
        """Load topics from CSV file.

        Returns:
            List of Topic objects

        Raises:
            TopicLoadError: If CSV file not found or invalid
        """
        if not self._topics_csv.exists():
            raise TopicLoadError(f"Input CSV not found: {self._topics_csv}")

        self._topics = []

        try:
            with open(self._topics_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    topic = Topic.from_dict(row)
                    if topic.is_valid:
                        self._topics.append(topic)
        except Exception as e:
            raise TopicLoadError(f"Failed to read CSV: {e}")

        return self._topics

    @property
    def topics(self) -> List[Topic]:
        """Get loaded topics."""
        return self._topics

    def __len__(self) -> int:
        """Get number of topics."""
        return len(self._topics)

    def __iter__(self):
        """Iterate over topics."""
        return iter(self._topics)
