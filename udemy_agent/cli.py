"""Command-line interface for Udemy Agent."""

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv

from udemy_agent.config import settings
from udemy_agent.core import UdemyAgent
from udemy_agent.services.browser_service import STEALTH_AVAILABLE


def setup_logging():
    """Configure logging based on settings."""
    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper(), logging.INFO),
        format=settings.logging.format
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Udemy Course Discovery Agent (LangGraph)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  udemy-agent                   # Run interactive CLI
  udemy-agent --headless        # Run with headless browser

Environment Variables:
  GROQ_API_KEY          Groq API key (required)
  LLM_MODEL             Model name (default: openai-gpt-oss-20b)
  BROWSER_HEADLESS      Run browser headless (true/false)
  LANGCHAIN_TRACING_V2  Enable LangSmith tracing (true/false)
  LANGCHAIN_API_KEY     LangSmith API key
  LANGCHAIN_PROJECT     LangSmith project name
        """
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    return parser.parse_args()


async def async_main():
    """Async entry point."""
    load_dotenv()
    args = parse_args()

    if args.verbose:
        settings.logging.level = "DEBUG"

    setup_logging()

    if args.headless:
        settings.browser.headless = True

    print("=" * 60)
    print("Udemy Course Discovery Agent (LangGraph)")
    print("=" * 60)

    if STEALTH_AVAILABLE:
        print("  Stealth mode: ENABLED")
    else:
        print("  Stealth mode: DISABLED (import error)")

    if settings.tracing.enabled:
        print(f"  LangSmith tracing: ENABLED (Project: {settings.tracing.project})")
    else:
        print("  LangSmith tracing: DISABLED")
        print("  To enable, set LANGCHAIN_TRACING_V2=true and LANGCHAIN_API_KEY in .env")

    print("\nI can help you discover Udemy courses!")
    print("Try asking:")
    print("  - 'What are the trending courses?'")
    print("  - 'Show me top-rated courses'")
    print("  - 'Find Python courses'")
    print("  - 'Search for machine learning courses'")
    print("  - 'Show me details of course 1'")
    print("  - 'Compare course 1 and 2'")
    print("\nType 'quit' or 'exit' to stop.")
    print("-" * 60)

    agent = UdemyAgent()

    try:
        while True:
            try:
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\nGoodbye!")
                    break

                if user_input.lower() == "clear":
                    agent.clear_history()
                    print("Conversation history cleared.")
                    continue

                print("\nAssistant: Thinking...")
                response = await agent.chat(user_input)
                print(f"\nAssistant: {response}")

            except KeyboardInterrupt:
                print("\n\nInterrupted. Goodbye!")
                break

    finally:
        await agent.close()

    return 0


def main():
    """CLI entry point."""
    try:
        sys.exit(asyncio.run(async_main()))
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
