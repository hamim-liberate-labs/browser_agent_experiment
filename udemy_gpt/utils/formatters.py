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
    objectives = "\n".join(f"- {obj}" for obj in details.objectives[:10]) if details.objectives else "- Not available"
    requirements = "\n".join(f"- {req}" for req in details.requirements[:8]) if details.requirements else "- Not available"

    # Format curriculum - handle both dict format and string format
    curriculum_items = []
    if details.curriculum:
        for c in details.curriculum[:20]:  # Show up to 20 sections
            if isinstance(c, dict):
                title = c.get('title', c.get('section', c.get('section_title', 'Section')))
                lectures = c.get('lectures', c.get('lecture_info', c.get('lectures_count', '')))
                duration = c.get('duration', c.get('section_duration', ''))
                # Build section info string
                info_parts = []
                if lectures:
                    info_parts.append(str(lectures))
                if duration:
                    info_parts.append(str(duration))
                if info_parts:
                    curriculum_items.append(f"- **{title}** ({' • '.join(info_parts)})")
                else:
                    curriculum_items.append(f"- {title}")
            elif isinstance(c, str):
                curriculum_items.append(f"- {c}")
    curriculum = "\n".join(curriculum_items) if curriculum_items else "- Not available"

    target_audience = "\n".join(f"- {t}" for t in details.target_audience[:8]) if details.target_audience else "- Not specified"

    reviews_list = []
    if details.reviews:
        for r in details.reviews[:5]:
            content = r.get("content", "")[:300]
            rating = r.get("rating", "")
            date = r.get("date", "")
            if content:
                header = []
                if rating:
                    header.append(f"⭐ {rating}")
                if date:
                    header.append(f"📅 {date}")
                header_str = " | ".join(header) if header else ""
                if header_str:
                    reviews_list.append(f"**{header_str}**\n> {content}")
                else:
                    reviews_list.append(f"> {content}")
    reviews = "\n\n".join(reviews_list) if reviews_list else "> No reviews available"

    # Build "This course includes" section
    course_includes = []
    if details.duration:
        course_includes.append(f"- {details.duration}")
    if details.articles:
        course_includes.append(f"- {details.articles}")
    if details.resources:
        course_includes.append(f"- {details.resources}")
    if details.coding_exercises:
        course_includes.append(f"- {details.coding_exercises}")
    if details.certificate:
        course_includes.append(f"- {details.certificate}")
    course_includes_text = "\n".join(course_includes) if course_includes else "- Not available"

    # Build course content summary
    content_summary = []
    if details.sections_count:
        content_summary.append(details.sections_count)
    if details.lectures_count:
        content_summary.append(details.lectures_count)
    if details.total_length:
        content_summary.append(details.total_length)
    content_summary_text = " • ".join(content_summary) if content_summary else "Not available"

    # Description (truncated if too long)
    description = details.description[:1500] + "..." if len(details.description) > 1500 else details.description
    description = description if description else "Not available"

    # Instructor bio (truncated if too long)
    instructor_bio = details.instructor_bio[:800] + "..." if len(details.instructor_bio) > 800 else details.instructor_bio

    # Format rating breakdown
    rating_breakdown_text = ""
    if details.rating_breakdown:
        breakdown_items = []
        for stars in ["5_star", "4_star", "3_star", "2_star", "1_star"]:
            if stars in details.rating_breakdown:
                star_label = stars.replace("_star", " star")
                breakdown_items.append(f"| {star_label} | {details.rating_breakdown[stars]} |")
        if breakdown_items:
            rating_breakdown_text = "| Stars | Percentage |\n|-------|------------|\n" + "\n".join(breakdown_items)

    return f"""
## Course Details (Live from Udemy)
### {details.title}
*{details.subtitle}*

| Attribute | Value |
|-----------|-------|
| **URL** | {details.url} |
| **Rating** | {details.rating} ({details.ratings_count}) |
| **Students** | {details.students} |
| **Created by** | {details.created_by} |
| **Last Updated** | {details.last_updated} |
| **Language** | {details.language} |
| **Level** | {details.level} |
| **Current Price** | {details.price} |
| **Original Price** | {details.original_price} |

---
### What you'll learn
{objectives}

---
### This course includes
{course_includes_text}

---
### Course content
**{content_summary_text}**

{curriculum}

---
### Requirements
{requirements}

---
### Description
{description}

---
### Who this course is for
{target_audience}

---
### Instructors
**{details.instructor_name}**
*{details.instructor_title}*

| Stat | Value |
|------|-------|
| **Instructor Rating** | {details.instructor_rating} |
| **Reviews** | {details.instructor_reviews} |
| **Students** | {details.instructor_students} |
| **Courses** | {details.instructor_courses} |

{instructor_bio}

---
### Student feedback
**{details.course_rating}** | **{details.ratings_count}**

{rating_breakdown_text}

---
### Reviews
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
