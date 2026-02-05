"""Formatting utilities for course display.

Provides functions to format course data for LLM context and user display.
"""

from typing import Any, Dict, List

from udemy_gpt.utils.parsers import parse_rating, parse_duration
from udemy_gpt.models import CourseDetails


def describe_filters(filters: Dict) -> str:
    """Create human-readable filter description.

    Args:
        filters: Filter dictionary

    Returns:
        Human-readable description string
    """
    if not filters:
        return "None"

    parts = []
    if filters.get("min_rating"):
        parts.append(f"rating {filters['min_rating']}+")
    if filters.get("max_duration"):
        parts.append(f"up to {filters['max_duration']}h")
    if filters.get("min_duration"):
        parts.append(f"at least {filters['min_duration']}h")
    if filters.get("max_price"):
        parts.append(f"under ${filters['max_price']}")
    if filters.get("level"):
        parts.append(f"{filters['level']} level")
    if filters.get("is_free"):
        parts.append("free only")
    if filters.get("limit"):
        parts.append(f"top {filters['limit']}")

    return ", ".join(parts) if parts else "None"


def format_conversation_context(messages: List[Dict[str, str]], max_messages: int = 10) -> str:
    """Get formatted conversation history for context.

    Args:
        messages: List of message dictionaries
        max_messages: Maximum messages to include

    Returns:
        Formatted conversation string
    """
    recent = messages[-max_messages:]
    if not recent:
        return ""

    parts = []
    for msg in recent:
        role = "User" if msg["role"] == "user" else "Assistant"
        content = msg["content"][:500] + "..." if len(msg["content"]) > 500 else msg["content"]
        parts.append(f"{role}: {content}")

    return "\n".join(parts)


def format_courses_for_llm(courses: List[Dict]) -> str:
    """Format courses for LLM context in markdown.

    Args:
        courses: List of course dictionaries

    Returns:
        Markdown formatted course list
    """
    if not courses:
        return "No courses found."

    text = ""
    for i, course in enumerate(courses, 1):
        title = course.get("title", "Unknown")
        url = course.get("url", "")
        instructor = course.get("instructor", "N/A")
        rating = parse_rating(str(course.get("rating", "N/A")))
        reviews = course.get("reviews_count", "N/A")
        price = course.get("price", "N/A")
        duration = parse_duration(str(course.get("duration", "N/A")))
        level = course.get("level", "N/A")
        bestseller = "Yes" if str(course.get("bestseller", "")).lower() in ("true", "yes", "1") else "No"
        topic = course.get("topic", "N/A")
        url_display = f"[Enroll Here]({url})" if url else "N/A"

        text += f"""
---
### {i}. {title}
| Attribute | Value |
|-----------|-------|
| **URL** | {url_display} |
| **Instructor** | {instructor} |
| **Rating** | {rating}/5 ({reviews} reviews) |
| **Price** | {price} |
| **Duration** | {duration} hours |
| **Level** | {level} |
| **Bestseller** | {bestseller} |
| **Topic** | {topic} |
"""
    return text


def format_live_details(details: CourseDetails) -> str:
    """Format live course details in markdown.

    Args:
        details: CourseDetails from browser fetch

    Returns:
        Markdown formatted details
    """
    objectives = "\n".join(f"- {obj}" for obj in details.objectives[:8]) if details.objectives else "- Not available"
    requirements = "\n".join(f"- {req}" for req in details.requirements[:5]) if details.requirements else "- Not available"
    curriculum = "\n".join(f"- {c.get('section', 'Section')}" for c in details.curriculum[:8]) if details.curriculum else "- Not available"

    reviews_list = []
    if details.reviews:
        for r in details.reviews[:3]:
            content = r.get("content", "")[:200]
            if content:
                reviews_list.append(f"> {content}")
    reviews = "\n\n".join(reviews_list) if reviews_list else "> No reviews available"

    return f"""
## Course Details (Live from Udemy)
### {details.title}
*{details.subtitle}*

| Attribute | Value |
|-----------|-------|
| **URL** | {details.url} |
| **Rating** | {details.rating} ({details.reviews_count} reviews) |
| **Students** | {details.students} |
| **Last Updated** | {details.last_updated} |
| **Level** | {details.level} |
| **Current Price** | {details.price} |
| **Original Price** | {details.original_price} |
| **Duration** | {details.duration} |
| **Lectures** | {details.lectures} |
| **Sections** | {details.sections} |

---
### What You'll Learn
{objectives}

---
### Requirements
{requirements}

---
### Curriculum (Preview)
{curriculum}

---
### Instructor
**{details.instructor_name}**
{details.instructor_title}

---
### Recent Reviews
{reviews}
"""


def format_kb_details(course: Dict) -> str:
    """Format course details from knowledge base in markdown.

    Args:
        course: Course dictionary from CSV

    Returns:
        Markdown formatted details
    """
    bestseller = "Yes" if str(course.get("bestseller", "")).lower() in ("true", "yes", "1") else "No"
    url = course.get("url", "")
    url_display = f"[Enroll Here]({url})" if url else "N/A"

    return f"""
## Course Details (From Knowledge Base)
### {course.get('title', 'N/A')}

**Direct Link:** {url_display}

---
| Attribute | Value |
|-----------|-------|
| **Instructor** | {course.get('instructor', 'N/A')} |
| **Rating** | {course.get('rating', 'N/A')} ({course.get('reviews_count', 'N/A')} reviews) |
| **Level** | {course.get('level', 'N/A')} |
| **Price** | {course.get('price', 'N/A')} |
| **Duration** | {course.get('duration', 'N/A')} |
| **Lectures** | {course.get('lectures', 'N/A')} |
| **Bestseller** | {bestseller} |
| **Topic** | {course.get('topic', 'N/A')} |

---
> **Tip:** Ask for "live details" to get current information from Udemy.
"""


def format_comparison(courses: List[Dict]) -> str:
    """Format courses for comparison.

    Args:
        courses: List of courses to compare

    Returns:
        Markdown formatted comparison
    """
    text = ""
    for i, course in enumerate(courses, 1):
        url = course.get("url", "")
        url_display = f"[Enroll Here]({url})" if url else "N/A"
        bestseller = "Yes" if str(course.get("bestseller", "")).lower() in ("true", "yes", "1") else "No"

        text += f"""
### Course {i}: {course.get('title', 'Unknown')}
| Attribute | Value |
|-----------|-------|
| **URL** | {url_display} |
| **Instructor** | {course.get('instructor', 'N/A')} |
| **Rating** | {course.get('rating', 'N/A')} ({course.get('reviews_count', 'N/A')} reviews) |
| **Price** | {course.get('price', 'N/A')} |
| **Duration** | {course.get('duration', 'N/A')} |
| **Level** | {course.get('level', 'N/A')} |
| **Bestseller** | {bestseller} |
"""
    return text
