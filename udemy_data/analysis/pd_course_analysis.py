"""
Personal Development Course Data Analysis Script
Analyzes Udemy course data from the Personal Development category.
Generates two reports:
1. Bestselling + Personal Development combined analysis
2. Personal Development only analysis

Features:
- Handles duplicate courses across topics
- Includes full course details with URLs
"""

import csv
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from datetime import datetime


class CourseData:
    """Represents a single course with parsed data."""

    def __init__(self, row: dict, topic: str, source: str = "PD"):
        self.topics: Set[str] = {topic}  # Track all topics this course appears in
        self.source = source
        self.title = row.get('title', '').strip()
        self.url = row.get('url', '').strip()
        self.instructor = row.get('instructor', '').strip()
        self.rating = self._parse_rating(row.get('rating', ''))
        self.reviews_count = self._parse_reviews(row.get('reviews_count', ''))
        self.price = self._parse_price(row.get('price', ''))
        self.original_price = self._parse_price(row.get('original_price', ''))
        self.duration_hours = self._parse_duration(row.get('duration', ''))
        self.duration_raw = row.get('duration', '').strip()
        self.lectures = self._parse_lectures(row.get('lectures', ''))
        self.lectures_raw = row.get('lectures', '').strip()
        self.level = row.get('level', '').strip()

    def add_topic(self, topic: str):
        """Add another topic this course belongs to."""
        self.topics.add(topic)

    def get_topics_str(self) -> str:
        """Get comma-separated list of topics."""
        return ", ".join(sorted(self.topics))

    def _parse_rating(self, rating_str: str) -> Optional[float]:
        if not rating_str:
            return None
        try:
            match = re.search(r'(\d+\.?\d*)', rating_str)
            if match:
                return float(match.group(1))
        except (ValueError, TypeError):
            pass
        return None

    def _parse_reviews(self, reviews_str: str) -> Optional[int]:
        if not reviews_str:
            return None
        try:
            clean = reviews_str.replace(',', '').replace('"', '').strip()
            match = re.search(r'(\d+)', clean)
            if match:
                return int(match.group(1))
        except (ValueError, TypeError):
            pass
        return None

    def _parse_price(self, price_str: str) -> Optional[float]:
        if not price_str:
            return None
        try:
            clean = price_str.replace('$', '').replace(',', '').strip()
            if clean and clean != '':
                return float(clean)
        except (ValueError, TypeError):
            pass
        return None

    def _parse_duration(self, duration_str: str) -> Optional[float]:
        if not duration_str:
            return None
        try:
            hours_match = re.search(r'(\d+\.?\d*)\s*(?:total\s+)?hours?', duration_str.lower())
            if hours_match:
                return float(hours_match.group(1))
            mins_match = re.search(r'(\d+)\s*mins?', duration_str.lower())
            if mins_match:
                return float(mins_match.group(1)) / 60
        except (ValueError, TypeError):
            pass
        return None

    def _parse_lectures(self, lectures_str: str) -> Optional[int]:
        if not lectures_str:
            return None
        try:
            match = re.search(r'(\d+)', lectures_str)
            if match:
                return int(match.group(1))
        except (ValueError, TypeError):
            pass
        return None


class CourseAnalyzer:
    """Analyzes course data with deduplication support."""

    def __init__(self, name: str = "Analysis"):
        self.name = name
        self.courses_by_url: Dict[str, CourseData] = {}  # URL -> Course (deduplicated)
        self.topics: Dict[str, List[CourseData]] = defaultdict(list)
        self.duplicate_count = 0
        self.total_entries = 0

    @property
    def courses(self) -> List[CourseData]:
        """Get list of unique courses."""
        return list(self.courses_by_url.values())

    def load_from_directory(self, data_dir: str, source: str = "PD"):
        """Load all CSV files from a directory with deduplication."""
        data_path = Path(data_dir)
        if not data_path.exists():
            print(f"Directory not found: {data_dir}")
            return

        csv_files = list(data_path.glob('*.csv'))
        print(f"Found {len(csv_files)} CSV files in {source}")

        entries_before = self.total_entries
        duplicates_before = self.duplicate_count

        for csv_file in csv_files:
            topic = csv_file.stem.replace('-', ' ').title()
            try:
                with open(csv_file, 'r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('title') and row['title'].strip():
                            self.total_entries += 1
                            url = row.get('url', '').strip()

                            if url and url in self.courses_by_url:
                                # Duplicate found - add topic to existing course
                                self.courses_by_url[url].add_topic(topic)
                                self.topics[topic].append(self.courses_by_url[url])
                                self.duplicate_count += 1
                            else:
                                # New course
                                course = CourseData(row, topic, source)
                                if course.title:
                                    if url:
                                        self.courses_by_url[url] = course
                                    else:
                                        # No URL - use title as key (less reliable)
                                        self.courses_by_url[f"no_url_{len(self.courses_by_url)}_{course.title[:50]}"] = course
                                    self.topics[topic].append(course)
            except Exception as e:
                print(f"Error reading {csv_file}: {e}")

        new_entries = self.total_entries - entries_before
        new_duplicates = self.duplicate_count - duplicates_before
        unique_added = new_entries - new_duplicates

        print(f"Loaded from {source}: {new_entries} entries, {new_duplicates} duplicates, {unique_added} unique courses")
        print(f"Total unique courses so far: {len(self.courses_by_url)}")

    def overall_statistics(self) -> dict:
        """Calculate overall statistics."""
        unique_courses = self.courses
        courses_with_rating = [c for c in unique_courses if c.rating is not None]
        courses_with_price = [c for c in unique_courses if c.price is not None]
        courses_with_duration = [c for c in unique_courses if c.duration_hours is not None]
        courses_with_reviews = [c for c in unique_courses if c.reviews_count is not None]

        pd_courses = [c for c in unique_courses if c.source == "PD"]
        bs_courses = [c for c in unique_courses if c.source == "Bestselling"]

        # Multi-topic courses
        multi_topic_courses = [c for c in unique_courses if len(c.topics) > 1]

        return {
            'total_entries': self.total_entries,
            'total_unique_courses': len(unique_courses),
            'duplicate_entries': self.duplicate_count,
            'multi_topic_courses': len(multi_topic_courses),
            'total_topics': len(self.topics),
            'pd_courses': len(pd_courses),
            'bestselling_courses': len(bs_courses),
            'avg_rating': sum(c.rating for c in courses_with_rating) / len(courses_with_rating) if courses_with_rating else 0,
            'avg_price': sum(c.price for c in courses_with_price) / len(courses_with_price) if courses_with_price else 0,
            'avg_duration': sum(c.duration_hours for c in courses_with_duration) / len(courses_with_duration) if courses_with_duration else 0,
            'total_reviews': sum(c.reviews_count for c in courses_with_reviews),
            'avg_reviews': sum(c.reviews_count for c in courses_with_reviews) / len(courses_with_reviews) if courses_with_reviews else 0,
        }

    def pricing_analysis(self) -> dict:
        """Analyze pricing distribution."""
        courses_with_price = [c for c in self.courses if c.price is not None]
        prices = [c.price for c in courses_with_price]

        if not prices:
            return {}

        price_ranges = {
            'Free ($0)': 0,
            'Budget ($1-$29.99)': 0,
            'Mid-range ($30-$59.99)': 0,
            'Premium ($60-$99.99)': 0,
            'High-end ($100+)': 0
        }

        for p in prices:
            if p == 0:
                price_ranges['Free ($0)'] += 1
            elif p < 30:
                price_ranges['Budget ($1-$29.99)'] += 1
            elif p < 60:
                price_ranges['Mid-range ($30-$59.99)'] += 1
            elif p < 100:
                price_ranges['Premium ($60-$99.99)'] += 1
            else:
                price_ranges['High-end ($100+)'] += 1

        sorted_by_price = sorted(courses_with_price, key=lambda x: x.price, reverse=True)[:10]

        return {
            'min_price': min(prices),
            'max_price': max(prices),
            'avg_price': sum(prices) / len(prices),
            'median_price': sorted(prices)[len(prices) // 2],
            'price_ranges': price_ranges,
            'most_expensive': sorted_by_price
        }

    def rating_analysis(self) -> dict:
        """Analyze rating distribution."""
        courses_with_rating = [c for c in self.courses if c.rating is not None]
        ratings = [c.rating for c in courses_with_rating]

        if not ratings:
            return {}

        rating_dist = {
            '5.0': 0,
            '4.5-4.9': 0,
            '4.0-4.4': 0,
            '3.5-3.9': 0,
            '3.0-3.4': 0,
            'Below 3.0': 0
        }

        for r in ratings:
            if r == 5.0:
                rating_dist['5.0'] += 1
            elif r >= 4.5:
                rating_dist['4.5-4.9'] += 1
            elif r >= 4.0:
                rating_dist['4.0-4.4'] += 1
            elif r >= 3.5:
                rating_dist['3.5-3.9'] += 1
            elif r >= 3.0:
                rating_dist['3.0-3.4'] += 1
            else:
                rating_dist['Below 3.0'] += 1

        significant_courses = [c for c in courses_with_rating if c.reviews_count and c.reviews_count >= 100]
        top_rated = sorted(significant_courses, key=lambda x: (x.rating, x.reviews_count), reverse=True)[:10]

        return {
            'min_rating': min(ratings),
            'max_rating': max(ratings),
            'avg_rating': sum(ratings) / len(ratings),
            'rating_distribution': rating_dist,
            'top_rated_courses': top_rated
        }

    def instructor_analysis(self) -> dict:
        """Analyze instructor statistics."""
        instructor_courses = defaultdict(list)
        for course in self.courses:
            if course.instructor:
                instructor_courses[course.instructor].append(course)

        prolific = sorted(instructor_courses.items(), key=lambda x: len(x[1]), reverse=True)[:15]

        instructor_stats = []
        for instructor, courses in instructor_courses.items():
            if len(courses) >= 3:
                rated_courses = [c for c in courses if c.rating is not None]
                if rated_courses:
                    avg_rating = sum(c.rating for c in rated_courses) / len(rated_courses)
                    total_reviews = sum(c.reviews_count for c in courses if c.reviews_count)
                    instructor_stats.append({
                        'name': instructor,
                        'avg_rating': avg_rating,
                        'course_count': len(courses),
                        'total_reviews': total_reviews,
                        'courses': courses
                    })

        best_rated = sorted(instructor_stats, key=lambda x: (x['avg_rating'], x['total_reviews']), reverse=True)[:10]

        return {
            'total_instructors': len(instructor_courses),
            'avg_courses_per_instructor': len(self.courses) / len(instructor_courses) if instructor_courses else 0,
            'prolific_instructors': [(i, c) for i, c in prolific],
            'best_rated_instructors': best_rated
        }

    def duration_analysis(self) -> dict:
        """Analyze course duration distribution."""
        courses_with_duration = [c for c in self.courses if c.duration_hours is not None and c.duration_hours < 500]  # Filter outliers
        durations = [c.duration_hours for c in courses_with_duration]

        if not durations:
            return {}

        duration_ranges = {
            'Short (< 2 hours)': 0,
            'Medium (2-5 hours)': 0,
            'Long (5-10 hours)': 0,
            'Extended (10-20 hours)': 0,
            'Comprehensive (20+ hours)': 0
        }

        for d in durations:
            if d < 2:
                duration_ranges['Short (< 2 hours)'] += 1
            elif d < 5:
                duration_ranges['Medium (2-5 hours)'] += 1
            elif d < 10:
                duration_ranges['Long (5-10 hours)'] += 1
            elif d < 20:
                duration_ranges['Extended (10-20 hours)'] += 1
            else:
                duration_ranges['Comprehensive (20+ hours)'] += 1

        longest = sorted(courses_with_duration, key=lambda x: x.duration_hours, reverse=True)[:10]

        return {
            'min_duration': min(durations),
            'max_duration': max(durations),
            'avg_duration': sum(durations) / len(durations),
            'total_hours': sum(durations),
            'duration_ranges': duration_ranges,
            'longest_courses': longest
        }

    def level_analysis(self) -> dict:
        """Analyze course level distribution."""
        level_counts = defaultdict(int)
        for course in self.courses:
            if course.level:
                level_counts[course.level] += 1
            else:
                level_counts['Not Specified'] += 1

        return {
            'level_distribution': dict(level_counts),
            'total_categorized': sum(v for k, v in level_counts.items() if k != 'Not Specified')
        }

    def topic_analysis(self) -> dict:
        """Analyze topics popularity and statistics."""
        topic_stats = []

        for topic, courses in self.topics.items():
            # Get unique courses for this topic
            unique_urls = set()
            unique_courses = []
            for c in courses:
                if c.url not in unique_urls:
                    unique_urls.add(c.url)
                    unique_courses.append(c)

            rated = [c for c in unique_courses if c.rating is not None]
            reviewed = [c for c in unique_courses if c.reviews_count is not None]
            priced = [c for c in unique_courses if c.price is not None]

            stats = {
                'topic': topic,
                'course_count': len(unique_courses),
                'avg_rating': sum(c.rating for c in rated) / len(rated) if rated else 0,
                'total_reviews': sum(c.reviews_count for c in reviewed),
                'avg_price': sum(c.price for c in priced) / len(priced) if priced else 0
            }
            topic_stats.append(stats)

        by_courses = sorted(topic_stats, key=lambda x: x['course_count'], reverse=True)[:15]
        by_reviews = sorted(topic_stats, key=lambda x: x['total_reviews'], reverse=True)[:15]
        by_rating = sorted([t for t in topic_stats if t['course_count'] >= 5],
                          key=lambda x: x['avg_rating'], reverse=True)[:15]

        return {
            'topics_by_course_count': by_courses,
            'topics_by_popularity': by_reviews,
            'topics_by_rating': by_rating
        }

    def value_analysis(self) -> dict:
        """Analyze value (rating vs price relationship)."""
        courses_with_both = [c for c in self.courses
                           if c.rating is not None and c.price is not None and c.reviews_count and c.reviews_count >= 50]

        if not courses_with_both:
            return {}

        for c in courses_with_both:
            c.value_score = (c.rating * c.reviews_count) / (c.price + 1)

        best_value = sorted(courses_with_both, key=lambda x: x.value_score, reverse=True)[:15]

        return {
            'best_value_courses': best_value
        }

    def content_depth_analysis(self) -> dict:
        """Analyze content depth (lectures and duration)."""
        courses_with_lectures = [c for c in self.courses if c.lectures is not None and c.duration_hours is not None and c.duration_hours < 500]

        if not courses_with_lectures:
            return {}

        for c in courses_with_lectures:
            if c.lectures > 0:
                c.avg_lecture_length = (c.duration_hours * 60) / c.lectures

        courses_with_avg = [c for c in courses_with_lectures if hasattr(c, 'avg_lecture_length')]
        most_lectures = sorted(courses_with_lectures, key=lambda x: x.lectures, reverse=True)[:10]

        return {
            'avg_lectures_per_course': sum(c.lectures for c in courses_with_lectures) / len(courses_with_lectures),
            'avg_lecture_length_mins': sum(c.avg_lecture_length for c in courses_with_avg) / len(courses_with_avg) if courses_with_avg else 0,
            'most_comprehensive': most_lectures
        }

    def review_engagement_analysis(self) -> dict:
        """Analyze review engagement patterns."""
        courses_with_reviews = [c for c in self.courses if c.reviews_count is not None]

        if not courses_with_reviews:
            return {}

        reviews = [c.reviews_count for c in courses_with_reviews]

        review_ranges = {
            'Low (1-100)': 0,
            'Medium (101-500)': 0,
            'High (501-1000)': 0,
            'Very High (1001-5000)': 0,
            'Exceptional (5000+)': 0
        }

        for r in reviews:
            if r <= 100:
                review_ranges['Low (1-100)'] += 1
            elif r <= 500:
                review_ranges['Medium (101-500)'] += 1
            elif r <= 1000:
                review_ranges['High (501-1000)'] += 1
            elif r <= 5000:
                review_ranges['Very High (1001-5000)'] += 1
            else:
                review_ranges['Exceptional (5000+)'] += 1

        most_reviewed = sorted(courses_with_reviews, key=lambda x: x.reviews_count, reverse=True)[:15]

        return {
            'total_reviews': sum(reviews),
            'avg_reviews': sum(reviews) / len(reviews),
            'max_reviews': max(reviews),
            'review_distribution': review_ranges,
            'most_reviewed_courses': most_reviewed
        }

    def source_comparison(self) -> dict:
        """Compare PD vs Bestselling courses."""
        pd_courses = [c for c in self.courses if c.source == "PD"]
        bs_courses = [c for c in self.courses if c.source == "Bestselling"]

        if not bs_courses:
            return {}

        def calc_stats(courses):
            rated = [c for c in courses if c.rating is not None]
            priced = [c for c in courses if c.price is not None]
            reviewed = [c for c in courses if c.reviews_count is not None]
            duration = [c for c in courses if c.duration_hours is not None and c.duration_hours < 500]

            return {
                'count': len(courses),
                'avg_rating': sum(c.rating for c in rated) / len(rated) if rated else 0,
                'avg_price': sum(c.price for c in priced) / len(priced) if priced else 0,
                'avg_reviews': sum(c.reviews_count for c in reviewed) / len(reviewed) if reviewed else 0,
                'avg_duration': sum(c.duration_hours for c in duration) / len(duration) if duration else 0,
            }

        return {
            'pd_stats': calc_stats(pd_courses),
            'bestselling_stats': calc_stats(bs_courses)
        }

    def multi_topic_analysis(self) -> dict:
        """Analyze courses that appear in multiple topics."""
        multi_topic = [c for c in self.courses if len(c.topics) > 1]
        multi_topic_sorted = sorted(multi_topic, key=lambda x: len(x.topics), reverse=True)[:20]

        return {
            'multi_topic_count': len(multi_topic),
            'top_multi_topic_courses': multi_topic_sorted
        }


def format_course_detail(course: CourseData, include_url: bool = True) -> str:
    """Format a single course with full details."""
    lines = []

    # Clean title - remove embedded descriptions
    title = course.title
    # Try to extract just the course name before "Rating:" if it's embedded
    if "Rating:" in title:
        title = title.split("Rating:")[0].strip()

    lines.append(f"**{title}**")

    if include_url and course.url:
        lines.append(f"- URL: {course.url}")

    lines.append(f"- Instructor: {course.instructor or 'N/A'}")
    lines.append(f"- Rating: {course.rating:.1f}/5.0" if course.rating else "- Rating: N/A")
    lines.append(f"- Reviews: {course.reviews_count:,}" if course.reviews_count else "- Reviews: N/A")
    lines.append(f"- Price: ${course.price:.2f}" if course.price else "- Price: N/A")
    lines.append(f"- Duration: {course.duration_raw or 'N/A'}")
    lines.append(f"- Lectures: {course.lectures_raw or 'N/A'}")
    lines.append(f"- Level: {course.level or 'N/A'}")
    lines.append(f"- Topics: {course.get_topics_str()}")
    lines.append(f"- Source: {course.source}")

    return "\n".join(lines)


def format_course_table_row(course: CourseData) -> str:
    """Format course as a detailed table section."""
    title = course.title
    if "Rating:" in title:
        title = title.split("Rating:")[0].strip()

    return f"""
#### {title}

| Field | Value |
|-------|-------|
| URL | {course.url or 'N/A'} |
| Instructor | {course.instructor or 'N/A'} |
| Rating | {f"{course.rating:.1f}/5.0" if course.rating else 'N/A'} |
| Reviews | {f"{course.reviews_count:,}" if course.reviews_count else 'N/A'} |
| Price | {f"${course.price:.2f}" if course.price else 'N/A'} |
| Duration | {course.duration_raw or 'N/A'} |
| Lectures | {course.lectures_raw or 'N/A'} |
| Level | {course.level or 'N/A'} |
| Topics | {course.get_topics_str()} |
| Source | {course.source} |
"""


def generate_markdown_report(analyzer: CourseAnalyzer, include_source_comparison: bool = False) -> str:
    """Generate comprehensive markdown report with full course details."""

    overall = analyzer.overall_statistics()
    pricing = analyzer.pricing_analysis()
    rating = analyzer.rating_analysis()
    instructor = analyzer.instructor_analysis()
    duration = analyzer.duration_analysis()
    level = analyzer.level_analysis()
    topic = analyzer.topic_analysis()
    value = analyzer.value_analysis()
    content = analyzer.content_depth_analysis()
    engagement = analyzer.review_engagement_analysis()
    multi_topic = analyzer.multi_topic_analysis()

    report = f"""# {analyzer.name}

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## Executive Summary

This report provides a comprehensive analysis of Udemy courses. The analysis covers pricing, ratings, instructors, duration, content depth, and topic popularity to provide actionable insights for learners, course creators, and market researchers.

### Key Highlights

| Metric | Value |
|--------|-------|
| Total CSV Entries | {overall['total_entries']:,} |
| Unique Courses | {overall['total_unique_courses']:,} |
| Duplicate Entries | {overall['duplicate_entries']:,} |
| Multi-Topic Courses | {overall['multi_topic_courses']:,} |
| Topics Covered | {overall['total_topics']} |
"""

    if include_source_comparison and overall.get('bestselling_courses', 0) > 0:
        report += f"""| Personal Development Courses | {overall['pd_courses']:,} |
| Bestselling Courses | {overall['bestselling_courses']:,} |
"""

    report += f"""| Average Rating | {overall['avg_rating']:.2f} / 5.0 |
| Average Price | ${overall['avg_price']:.2f} |
| Average Duration | {overall['avg_duration']:.1f} hours |
| Total Student Reviews | {overall['total_reviews']:,} |

---
"""

    # Source comparison section
    if include_source_comparison:
        source_comp = analyzer.source_comparison()
        if source_comp:
            pd_stats = source_comp['pd_stats']
            bs_stats = source_comp['bestselling_stats']
            report += f"""
## Source Comparison: Personal Development vs Bestselling

| Metric | Personal Development | Bestselling |
|--------|---------------------|-------------|
| Course Count | {pd_stats['count']:,} | {bs_stats['count']:,} |
| Average Rating | {pd_stats['avg_rating']:.2f} | {bs_stats['avg_rating']:.2f} |
| Average Price | ${pd_stats['avg_price']:.2f} | ${bs_stats['avg_price']:.2f} |
| Average Reviews | {pd_stats['avg_reviews']:.0f} | {bs_stats['avg_reviews']:.0f} |
| Average Duration | {pd_stats['avg_duration']:.1f} hrs | {bs_stats['avg_duration']:.1f} hrs |

### Key Observations

- **Course Volume:** Personal Development has {pd_stats['count']:,} courses vs {bs_stats['count']:,} Bestselling courses
- **Quality Comparison:** {'Bestselling courses have higher average ratings' if bs_stats['avg_rating'] > pd_stats['avg_rating'] else 'Personal Development courses have higher average ratings'}
- **Price Difference:** {'Bestselling courses are more expensive on average' if bs_stats['avg_price'] > pd_stats['avg_price'] else 'Personal Development courses are more expensive on average'}
- **Engagement:** {'Bestselling courses have more reviews on average' if bs_stats['avg_reviews'] > pd_stats['avg_reviews'] else 'Personal Development courses have more reviews on average'}

---
"""

    # Multi-topic courses section
    report += f"""
## Duplicate/Multi-Topic Course Analysis

Courses can appear in multiple topic categories. This section identifies courses that span multiple topics.

- **Total Multi-Topic Courses:** {multi_topic['multi_topic_count']:,}
- **Percentage of Total:** {(multi_topic['multi_topic_count'] / overall['total_unique_courses'] * 100):.1f}%

### Top Multi-Topic Courses

"""
    for i, course in enumerate(multi_topic.get('top_multi_topic_courses', [])[:10], 1):
        report += f"{i}. {format_course_detail(course)}\n\n"

    report += """
---

## 1. Pricing Analysis

### Price Distribution

| Price Range | Count | Percentage |
|-------------|-------|------------|
"""

    total_priced = sum(pricing['price_ranges'].values()) if pricing.get('price_ranges') else 1
    for range_name, count in pricing.get('price_ranges', {}).items():
        pct = (count / total_priced) * 100
        report += f"| {range_name} | {count} | {pct:.1f}% |\n"

    report += f"""
### Price Statistics

- **Minimum Price:** ${pricing.get('min_price', 0):.2f}
- **Maximum Price:** ${pricing.get('max_price', 0):.2f}
- **Average Price:** ${pricing.get('avg_price', 0):.2f}
- **Median Price:** ${pricing.get('median_price', 0):.2f}

### Top 10 Most Expensive Courses

"""
    for i, course in enumerate(pricing.get('most_expensive', []), 1):
        report += f"{i}. {format_course_detail(course)}\n\n"

    report += """
---

## 2. Rating Analysis

### Rating Distribution

| Rating Range | Count | Percentage |
|--------------|-------|------------|
"""

    total_rated = sum(rating['rating_distribution'].values()) if rating.get('rating_distribution') else 1
    for range_name, count in rating.get('rating_distribution', {}).items():
        pct = (count / total_rated) * 100
        report += f"| {range_name} | {count} | {pct:.1f}% |\n"

    report += f"""
### Rating Statistics

- **Average Rating:** {rating.get('avg_rating', 0):.2f} / 5.0
- **Minimum Rating:** {rating.get('min_rating', 0):.2f}
- **Maximum Rating:** {rating.get('max_rating', 0):.2f}

### Top 10 Highest Rated Courses (100+ Reviews)

"""
    for i, course in enumerate(rating.get('top_rated_courses', []), 1):
        report += f"{i}. {format_course_detail(course)}\n\n"

    report += f"""
---

## 3. Instructor Analysis

### Overview

- **Total Unique Instructors:** {instructor.get('total_instructors', 0):,}
- **Average Courses per Instructor:** {instructor.get('avg_courses_per_instructor', 0):.2f}

### Top 15 Most Prolific Instructors

| Rank | Instructor | Course Count |
|------|------------|--------------|
"""

    for i, (name, courses) in enumerate(instructor.get('prolific_instructors', []), 1):
        report += f"| {i} | {name[:60]} | {len(courses)} |\n"

    report += """
### Top 10 Best Rated Instructors (3+ Courses)

"""
    for i, inst in enumerate(instructor.get('best_rated_instructors', []), 1):
        report += f"""
#### {i}. {inst['name']}

| Metric | Value |
|--------|-------|
| Average Rating | {inst['avg_rating']:.2f} |
| Total Courses | {inst['course_count']} |
| Total Reviews | {inst['total_reviews']:,} |

"""

    report += f"""
---

## 4. Duration Analysis

### Duration Distribution

| Duration Range | Count | Percentage |
|----------------|-------|------------|
"""

    total_duration = sum(duration['duration_ranges'].values()) if duration.get('duration_ranges') else 1
    for range_name, count in duration.get('duration_ranges', {}).items():
        pct = (count / total_duration) * 100
        report += f"| {range_name} | {count} | {pct:.1f}% |\n"

    report += f"""
### Duration Statistics

- **Total Content Hours:** {duration.get('total_hours', 0):,.1f} hours
- **Average Duration:** {duration.get('avg_duration', 0):.1f} hours
- **Shortest Course:** {duration.get('min_duration', 0):.1f} hours
- **Longest Course:** {duration.get('max_duration', 0):.1f} hours

### Top 10 Longest Courses

"""
    for i, course in enumerate(duration.get('longest_courses', []), 1):
        report += f"{i}. {format_course_detail(course)}\n\n"

    report += f"""
---

## 5. Course Level Analysis

### Level Distribution

| Level | Count | Percentage |
|-------|-------|------------|
"""

    total_level = sum(level['level_distribution'].values()) if level.get('level_distribution') else 1
    for level_name, count in sorted(level.get('level_distribution', {}).items(), key=lambda x: x[1], reverse=True):
        pct = (count / total_level) * 100
        report += f"| {level_name} | {count} | {pct:.1f}% |\n"

    report += f"""
---

## 6. Topic Analysis

### Top 15 Topics by Course Count

| Rank | Topic | Courses | Avg Rating | Total Reviews | Avg Price |
|------|-------|---------|------------|---------------|-----------|
"""

    for i, t in enumerate(topic.get('topics_by_course_count', []), 1):
        report += f"| {i} | {t['topic']} | {t['course_count']} | {t['avg_rating']:.2f} | {t['total_reviews']:,} | ${t['avg_price']:.2f} |\n"

    report += """
### Top 15 Topics by Popularity (Total Reviews)

| Rank | Topic | Total Reviews | Courses | Avg Rating |
|------|-------|---------------|---------|------------|
"""

    for i, t in enumerate(topic.get('topics_by_popularity', []), 1):
        report += f"| {i} | {t['topic']} | {t['total_reviews']:,} | {t['course_count']} | {t['avg_rating']:.2f} |\n"

    report += """
### Top 15 Topics by Average Rating (5+ Courses)

| Rank | Topic | Avg Rating | Courses | Total Reviews |
|------|-------|------------|---------|---------------|
"""

    for i, t in enumerate(topic.get('topics_by_rating', []), 1):
        report += f"| {i} | {t['topic']} | {t['avg_rating']:.2f} | {t['course_count']} | {t['total_reviews']:,} |\n"

    report += f"""
---

## 7. Value Analysis

### Best Value Courses

*Value score calculated based on: (rating × reviews) / (price + 1)*

"""
    for i, course in enumerate(value.get('best_value_courses', []), 1):
        report += f"{i}. {format_course_detail(course)}\n\n"

    report += f"""
---

## 8. Content Depth Analysis

### Lecture Statistics

- **Average Lectures per Course:** {content.get('avg_lectures_per_course', 0):.1f}
- **Average Lecture Length:** {content.get('avg_lecture_length_mins', 0):.1f} minutes

### Top 10 Most Comprehensive Courses (by Lecture Count)

"""
    for i, course in enumerate(content.get('most_comprehensive', []), 1):
        report += f"{i}. {format_course_detail(course)}\n\n"

    report += f"""
---

## 9. Review Engagement Analysis

### Review Distribution

| Review Range | Count | Percentage |
|--------------|-------|------------|
"""

    total_reviewed = sum(engagement['review_distribution'].values()) if engagement.get('review_distribution') else 1
    for range_name, count in engagement.get('review_distribution', {}).items():
        pct = (count / total_reviewed) * 100
        report += f"| {range_name} | {count} | {pct:.1f}% |\n"

    report += f"""
### Engagement Statistics

- **Total Reviews:** {engagement.get('total_reviews', 0):,}
- **Average Reviews per Course:** {engagement.get('avg_reviews', 0):.1f}
- **Maximum Reviews:** {engagement.get('max_reviews', 0):,}

### Top 15 Most Reviewed Courses

"""
    for i, course in enumerate(engagement.get('most_reviewed_courses', []), 1):
        report += f"{i}. {format_course_detail(course)}\n\n"

    report += """
---

## 10. Key Insights and Recommendations

### For Learners

1. **Best Value Topics:** Focus on topics with high ratings and reasonable prices
2. **Quality Indicators:** Courses with 100+ reviews and 4.5+ ratings are generally reliable
3. **Time Investment:** Consider course duration when planning your learning journey
4. **Multi-Topic Courses:** Courses appearing in multiple topics may offer broader knowledge

### For Course Creators

1. **Market Opportunities:** Topics with fewer courses but high demand show opportunity
2. **Pricing Strategy:** Analyze the pricing distribution to position your course competitively
3. **Content Length:** Comprehensive courses tend to attract more engagement

### For Market Researchers

1. **Category Health:** High average ratings indicate strong content quality standards
2. **Instructor Ecosystem:** Diverse instructor base with multiple top performers
3. **Growth Areas:** Topics with high review counts indicate strong market demand

---

## Methodology

This analysis was conducted using raw course data extracted from Udemy. The following fields were analyzed:

- **Title:** Course name
- **URL:** Course link (used for deduplication)
- **Instructor:** Course creator
- **Rating:** Average student rating (1-5 scale)
- **Reviews Count:** Number of student reviews
- **Price:** Current course price in USD
- **Duration:** Total video content length
- **Lectures:** Number of video lectures
- **Level:** Target skill level (Beginner, Intermediate, etc.)

**Deduplication:** Courses appearing in multiple topic CSVs are identified by URL and counted once, with all topics tracked.

Data was processed using Python with CSV parsing and statistical analysis.

---

*Report generated automatically by Udemy Course Analyzer*
"""

    return report


def main():
    """Main entry point - generates two reports."""
    base_dir = Path(__file__).parent.parent
    pd_dir = base_dir / "courses" / "Personal Development"
    bs_dir = base_dir / "courses" / "Bestselling"
    output_dir = Path(__file__).parent

    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("UDEMY COURSE DATA ANALYSIS")
    print("=" * 60)

    # ========================================
    # Analysis 1: Personal Development Only
    # ========================================
    print("\n--- Analysis 1: Personal Development Only ---")
    pd_analyzer = CourseAnalyzer("Udemy Personal Development Course Analysis Report")
    pd_analyzer.load_from_directory(str(pd_dir), "PD")

    pd_report = generate_markdown_report(pd_analyzer, include_source_comparison=False)
    pd_output = output_dir / "Personal_Development_Only_Analysis.md"
    with open(pd_output, 'w', encoding='utf-8') as f:
        f.write(pd_report)
    print(f"Report saved to: {pd_output}")

    # ========================================
    # Analysis 2: Bestselling + Personal Development Combined
    # ========================================
    print("\n--- Analysis 2: Bestselling + Personal Development Combined ---")
    combined_analyzer = CourseAnalyzer("Udemy Bestselling + Personal Development Combined Analysis Report")
    combined_analyzer.load_from_directory(str(pd_dir), "PD")
    combined_analyzer.load_from_directory(str(bs_dir), "Bestselling")

    combined_report = generate_markdown_report(combined_analyzer, include_source_comparison=True)
    combined_output = output_dir / "Bestselling_Plus_PD_Combined_Analysis.md"
    with open(combined_output, 'w', encoding='utf-8') as f:
        f.write(combined_report)
    print(f"Report saved to: {combined_output}")

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"\nGenerated Reports:")
    print(f"  1. {pd_output}")
    print(f"  2. {combined_output}")

    return pd_report, combined_report


if __name__ == "__main__":
    main()
