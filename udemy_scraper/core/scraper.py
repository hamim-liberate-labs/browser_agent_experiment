"""Main scraper orchestrator."""

import asyncio
from typing import List

from playwright.async_api import Page

from udemy_scraper.config import get_scraper_settings
from udemy_scraper.data import CourseWriter, TopicRepository
from udemy_scraper.exceptions import CloudflareBlockedError
from udemy_scraper.models import ScrapedCourse, ScrapeResult, ScrapeSummary, Topic
from udemy_scraper.services import BrowserService, ExtractionService


class UdemyScraper:
    """Orchestrates scraping of Udemy course listings."""

    def __init__(
        self,
        topic_repository: TopicRepository = None,
        course_writer: CourseWriter = None,
        browser_service: BrowserService = None,
        extraction_service: ExtractionService = None,
    ):
        self._topic_repo = topic_repository or TopicRepository()
        self._writer = course_writer or CourseWriter()
        self._browser = browser_service or BrowserService()
        self._extractor = extraction_service or ExtractionService()
        self._scraper_settings = get_scraper_settings()

    async def scrape_topic(self, page: Page, topic: Topic) -> ScrapeResult:
        """Scrape courses from a single topic.

        Args:
            page: Playwright page
            topic: Topic to scrape

        Returns:
            ScrapeResult with courses and status
        """
        result = ScrapeResult(topic_name=topic.name, topic_slug=topic.slug)
        all_courses: List[ScrapedCourse] = []

        try:
            print(f"  Loading: {topic.url}")
            await self._browser.navigate(page, topic.url)
            await self._browser.delay(2.0, 3.0)

            if not await self._browser.wait_cloudflare(page, 20):
                result.error = "Cloudflare blocked"
                print(f"  ERROR: Cloudflare blocked")
                return result

            # Page 1
            print(f"  Scrolling page 1...")
            await self._browser.scroll_page(page)
            page1_courses = await self._extractor.extract_courses(page)
            print(f"  Page 1: {len(page1_courses)} courses")
            all_courses.extend(page1_courses)

            # Page 2
            if self._scraper_settings.pages_per_topic >= 2:
                print(f"  Going to page 2...")
                if await self._browser.click_page_2(page, topic.url):
                    await self._browser.wait_cloudflare(page, 10)
                    print(f"  Scrolling page 2...")
                    await self._browser.scroll_page(page)
                    page2_courses = await self._extractor.extract_courses(page)
                    print(f"  Page 2: {len(page2_courses)} courses")
                    all_courses.extend(page2_courses)
                else:
                    print(f"  Could not navigate to page 2")

            # Deduplicate
            unique_courses = self._extractor.deduplicate(all_courses)
            print(f"  Total: {len(unique_courses)} courses")

            result.courses = unique_courses
            result.success = True

        except Exception as e:
            result.error = str(e)
            print(f"  Scrape error: {e}")

        return result

    async def run(self, skip_existing: bool = None) -> ScrapeSummary:
        """Run the scraper on all topics.

        Args:
            skip_existing: Skip topics with existing output files

        Returns:
            ScrapeSummary with results
        """
        skip_existing = skip_existing if skip_existing is not None else self._scraper_settings.skip_existing

        print("=" * 60)
        print("Udemy Course Scraper")
        print("=" * 60)

        # Load topics
        topics = self._topic_repo.load()
        if not topics:
            print("No topics found!")
            return ScrapeSummary()

        print(f"Loaded {len(topics)} topics")
        print("=" * 60)

        # Setup
        self._writer.ensure_output_dir()
        summary = ScrapeSummary(
            total_topics=len(topics),
            output_dir=self._writer.output_dir
        )

        try:
            page = await self._browser.new_page()

            for i, topic in enumerate(topics, 1):
                print(f"\n[{i}/{len(topics)}] {topic.name}")

                if not topic.is_valid:
                    print(f"  Skipping: Invalid topic")
                    summary.add_skipped(topic.name)
                    continue

                if skip_existing and self._writer.exists(topic):
                    print(f"  Skipping: Already scraped")
                    summary.add_skipped(topic.name)
                    continue

                result = await self.scrape_topic(page, topic)

                if result.success and result.courses:
                    output_path = self._writer.save(result.courses, topic)
                    result.output_path = output_path
                    print(f"  Saved {len(result.courses)} courses to {output_path}")

                summary.add_result(result)
                await self._browser.delay()

            await page.close()

        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
        finally:
            await self._browser.close()

        print(summary.format_summary())
        return summary


async def run_scraper(skip_existing: bool = True) -> ScrapeSummary:
    """Convenience function to run the scraper.

    Args:
        skip_existing: Skip topics with existing output files

    Returns:
        ScrapeSummary with results
    """
    scraper = UdemyScraper()
    return await scraper.run(skip_existing=skip_existing)
