"""Command Line Interface for Udemy GPT.

This module provides the interactive CLI for the Udemy course
discovery assistant.

Usage:
    python -m udemy_gpt

Commands:
    /help     - Show help information
    /topics   - List available topics
    /stats    - Show knowledge base statistics
    /session  - Show session statistics
    /clear    - Clear conversation history
    /quit     - Exit the application
"""

import asyncio
import logging
import os
import sys
from typing import Optional

from dotenv import load_dotenv

from udemy_gpt.core import UdemyGPT
from udemy_gpt.data import get_available_topics
from udemy_gpt.config import settings

load_dotenv()


def setup_logging() -> None:
    """Configure logging based on settings."""
    logging.basicConfig(
        level=getattr(logging, settings.logging.level, logging.INFO),
        format=settings.logging.format,
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def print_banner() -> None:
    """Print welcome banner."""
    print("=" * 60)
    print("  UDEMY GPT - Course Discovery Assistant")
    print("=" * 60)
    print()
    print("I can help you find, compare, and discover Udemy courses.")
    print()
    print("Examples:")
    print("  - Find Python courses for beginners")
    print("  - What are the top-rated web development courses?")
    print("  - Compare Python vs JavaScript")
    print("  - Create a learning path for full-stack developer")
    print()
    print("Commands: /help, /topics, /stats, /session, /clear, /quit")
    print("=" * 60)
    print()


def print_help() -> None:
    """Print help information."""
    help_text = """
SEARCH QUERIES:
  - "Find [topic] courses"
  - "[topic] courses for beginners"

FILTERS (can be combined):
  - "rating 4.5+"
  - "under $20" / "free courses"
  - "up to 3 hours"
  - "beginner/intermediate/advanced level"
  - "top 10" / "best 5"

EXAMPLES:
  - "Top 10 AI courses with rating 4.5+ under 5 hours"
  - "Best free Python courses for beginners"
  - "Machine learning courses under $50"

COMPARISONS:
  - "Compare course 1 and 2"
  - "Python vs JavaScript"

TOP COURSES:
  - "Most valuable courses"
  - "Top-rated courses"
  - "Best free courses"

LEARNING PATHS:
  - "How to become an AI engineer"
  - "Learning path for data science"

COURSE DETAILS:
  - "Tell me about course 1"
  - "Get current details for course 2" (fetches from Udemy)

COMMANDS:
  /help    - Show this help
  /topics  - List available topics
  /stats   - Show knowledge base statistics
  /session - Show current session stats
  /clear   - Clear conversation history
  /quit    - Exit the program
"""
    print(help_text)


def print_topics() -> None:
    """Print available topics."""
    topics = get_available_topics()

    print("\nAvailable Topics:\n")

    # Group by section
    sections = {}
    for t in topics:
        section = t.get("section", "Other")
        if section not in sections:
            sections[section] = []
        sections[section].append(t)

    for section, section_topics in sections.items():
        print(f"\n{section}:")
        for t in sorted(section_topics, key=lambda x: x['course_count'], reverse=True)[:10]:
            print(f"  - {t['slug']} ({t['course_count']} courses)")

    print(f"\nTotal: {len(topics)} topics")


def print_stats() -> None:
    """Print knowledge base statistics."""
    topics = get_available_topics()
    total_courses = sum(t['course_count'] for t in topics)
    sections = list(set(t['section'] for t in topics))

    print("\nKnowledge Base Statistics:\n")
    print(f"  Topics:   {len(topics)}")
    print(f"  Courses:  {total_courses}")
    print(f"  Sections: {len(sections)}")
    print()

    for section in sections:
        section_topics = [t for t in topics if t['section'] == section]
        section_courses = sum(t['course_count'] for t in section_topics)
        print(f"  {section}: {len(section_topics)} topics, {section_courses} courses")


def print_session_stats(agent: UdemyGPT) -> None:
    """Print current session statistics."""
    stats = agent.get_session_stats()
    print(f"""
Session Statistics:
  Messages:       {stats['messages_count']}
  Search results: {stats['last_search_count']}
  Current intent: {stats['current_intent'] or 'None'}
  Last topic:     {stats['last_topic'] or 'None'}
  Total topics:   {stats['available_topics']}
""")


async def run_cli() -> None:
    """Run the interactive CLI."""
    setup_logging()
    logger = logging.getLogger("udemy_gpt.cli")

    print_banner()

    # Check for API key
    if not os.getenv("GROQ_API_KEY"):
        print("ERROR: GROQ_API_KEY not found in environment.")
        print("Please set it in your .env file:")
        print("  GROQ_API_KEY=your_api_key_here")
        return

    print("Initializing...")
    try:
        agent = UdemyGPT()
    except Exception as e:
        logger.error(f"Failed to initialize: {e}")
        print(f"ERROR: {e}")
        return

    print("Ready! Type your question or /help for commands.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()

                if not user_input:
                    continue

                cmd = user_input.lower()

                if cmd in ("/quit", "/exit", "/q"):
                    print("\nGoodbye!")
                    break

                if cmd == "/help":
                    print_help()
                    continue

                if cmd == "/topics":
                    print_topics()
                    continue

                if cmd == "/stats":
                    print_stats()
                    continue

                if cmd == "/session":
                    print_session_stats(agent)
                    continue

                if cmd == "/clear":
                    agent.clear_history()
                    print("\nConversation cleared.\n")
                    continue

                print("\nThinking...\n")
                response = await agent.chat(user_input)
                print(f"Assistant:\n{response}\n")
                print("-" * 60)

            except KeyboardInterrupt:
                print("\n\nInterrupted. Type /quit to exit.\n")
                continue

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nError: {e}")

    finally:
        await agent.close()


def main() -> None:
    """Entry point for the CLI."""
    asyncio.run(run_cli())


if __name__ == "__main__":
    main()
