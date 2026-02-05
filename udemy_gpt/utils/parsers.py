"""Parsing utilities for LLM responses and user input."""

from typing import Any, Dict


def extract_json(response: str) -> str:
    """Extract JSON from LLM response.

    Handles responses with ```json code blocks or raw JSON.

    Args:
        response: LLM response text

    Returns:
        Extracted JSON string
    """
    if "```json" in response:
        start = response.find("```json") + 7
        end = response.find("```", start)
        return response[start:end].strip()
    elif "{" in response:
        start = response.find("{")
        end = response.rfind("}") + 1
        return response[start:end]
    return "{}"


def parse_filters(raw_filters: Dict) -> Dict[str, Any]:
    """Parse and validate filter values from LLM response.

    Args:
        raw_filters: Raw filter dictionary from LLM

    Returns:
        Validated filter dictionary
    """
    if not raw_filters:
        return {}

    filters = {}

    # Numeric filters
    for key in ["min_rating", "max_price", "min_duration", "max_duration", "limit"]:
        value = raw_filters.get(key)
        if value is not None:
            try:
                filters[key] = float(value) if key != "limit" else int(value)
            except (ValueError, TypeError):
                pass

    # Level filter
    if raw_filters.get("level"):
        level = str(raw_filters["level"]).lower()
        if level in ("beginner", "intermediate", "advanced", "all levels"):
            filters["level"] = level

    # Boolean filters
    if raw_filters.get("is_free") is not None:
        filters["is_free"] = bool(raw_filters["is_free"])

    return filters


def parse_rating(value: str) -> float:
    """Parse rating string to float.

    Args:
        value: Rating string

    Returns:
        Rating as float (0-5)
    """
    try:
        clean = str(value).replace(",", ".").strip()
        return float(clean)
    except (ValueError, TypeError):
        return 0.0


def parse_duration(value: str) -> float:
    """Parse duration string to hours.

    Args:
        value: Duration string

    Returns:
        Duration in hours
    """
    try:
        clean = str(value).lower().replace("hours", "").replace("hour", "").replace("h", "").strip()
        return float(clean)
    except (ValueError, TypeError):
        return 0.0
