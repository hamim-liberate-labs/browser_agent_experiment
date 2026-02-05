"""Prompt loader utilities.

Loads prompt templates from YAML files in the templates directory.
"""

import yaml
from pathlib import Path
from typing import Dict

# Templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"

# Cache for loaded prompts
_prompt_cache: Dict[str, Dict] = {}


def load_prompt(filename: str) -> Dict:
    """Load prompt from YAML file.

    Args:
        filename: Name of the YAML file in templates directory

    Returns:
        Dictionary with prompt data

    Raises:
        FileNotFoundError: If prompt file doesn't exist
    """
    if filename in _prompt_cache:
        return _prompt_cache[filename]

    filepath = TEMPLATES_DIR / filename
    if not filepath.exists():
        raise FileNotFoundError(f"Prompt file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    _prompt_cache[filename] = data
    return data


def get_intent_prompt() -> str:
    """Get intent classification prompt.

    Returns:
        System prompt for intent classification
    """
    data = load_prompt("intent.yml")
    return data.get("system", "")


def get_analysis_prompt() -> str:
    """Get course analysis prompt.

    Returns:
        System prompt for course analysis
    """
    data = load_prompt("analysis.yml")
    return data.get("system", "")


def get_response_prompt(intent: str) -> str:
    """Get response prompt for specific intent.

    Args:
        intent: Intent type (search, compare, details, etc.)

    Returns:
        Response prompt for the intent
    """
    data = load_prompt("response.yml")

    # Map intents to prompt keys
    intent_map = {
        "search": "search",
        "recommend": "search",
        "filter": "search",
        "stats": "search",
        "compare": "compare",
        "compare_topics": "compare_topics",
        "cross_topic_analysis": "compare_topics",
        "top_valuable": "top_valuable",
        "learning_path": "learning_path",
        "details": "details",
        "chat": "chat",
    }

    key = intent_map.get(intent, "chat")
    return data.get(key, data.get("chat", ""))


def clear_cache() -> None:
    """Clear the prompt cache."""
    global _prompt_cache
    _prompt_cache.clear()
