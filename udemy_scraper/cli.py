"""Command-line interface for Udemy Scraper."""

import argparse
import asyncio
import logging
import sys

from dotenv import load_dotenv

from udemy_scraper.config import settings
from udemy_scraper.core import UdemyScraper


def setup_logging():
    """Configure logging based on settings."""
    logging.basicConfig(
        level=getattr(logging, settings.logging.level.upper(), logging.INFO),
        format=settings.logging.format
    )


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Udemy Course Scraper - Scrape course listings to CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  udemy-scraper                     # Run with defaults
  udemy-scraper --no-skip           # Re-scrape existing topics
  udemy-scraper --headless          # Run browser in headless mode

Environment Variables:
  UDEMY_DATA_DIR        Path to data directory
  BROWSER_HEADLESS      Run browser headless (true/false)
  SCRAPER_PAGES_PER_TOPIC  Pages to scrape per topic (default: 2)
        """
    )

    parser.add_argument(
        "--no-skip",
        action="store_true",
        help="Don't skip topics with existing output files"
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

    scraper = UdemyScraper()
    summary = await scraper.run(skip_existing=not args.no_skip)

    return 0 if summary.failure_count == 0 else 1


def main():
    """CLI entry point."""
    try:
        sys.exit(asyncio.run(async_main()))
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(130)


if __name__ == "__main__":
    main()
