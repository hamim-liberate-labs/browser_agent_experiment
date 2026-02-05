"""Course extraction service for scraping page content."""

from typing import List, Dict

from playwright.async_api import Page

from udemy_scraper.models import ScrapedCourse


# JavaScript extraction code
EXTRACTION_JS = """
() => {
    const courses = [];
    // Find course cards using multiple selectors
    const cards = document.querySelectorAll(
        '[data-purpose="course-card-container"], ' +
        '.course-card--course-card--3g0oc, ' +
        '[class*="course-card"], ' +
        '[data-component-class="course-card"]'
    );

    cards.forEach(card => {
        try {
            // Extract title
            const titleEl = card.querySelector(
                '[data-purpose="course-title-url"], h3[class*="course-title"], h3 a'
            );
            const title = titleEl ? titleEl.textContent.trim() : null;
            if (!title) return;

            // Extract URL
            const linkEl = card.querySelector('a[href*="/course/"]');
            let url = linkEl ? linkEl.getAttribute('href') : null;
            if (url && url.startsWith('/')) {
                url = 'https://www.udemy.com' + url;
            }

            // Extract instructor
            const instructorEl = card.querySelector(
                '[data-purpose="course-instructor"], [class*="instructor"]'
            );
            const instructor = instructorEl ? instructorEl.textContent.trim() : null;

            // Extract rating
            const ratingEl = card.querySelector(
                '[data-purpose="rating-number"], [class*="star-rating--rating-number"]'
            );
            const rating = ratingEl ? ratingEl.textContent.trim() : null;

            // Extract reviews count
            const reviewsEl = card.querySelector(
                '[data-purpose="review-count"], [class*="reviews-text"]'
            );
            let reviews_count = reviewsEl ? reviewsEl.textContent.trim() : null;
            if (reviews_count) {
                reviews_count = reviews_count.replace(/[()]/g, '').trim();
            }

            // Extract price
            const priceEl = card.querySelector(
                '[data-purpose="course-price-text"] span span, [class*="price-text--price-part"]'
            );
            const price = priceEl ? priceEl.textContent.trim() : null;

            // Extract original price
            const origPriceEl = card.querySelector(
                '[data-purpose="original-price-text"] span span, [class*="original-price"]'
            );
            const original_price = origPriceEl ? origPriceEl.textContent.trim() : null;

            // Extract duration and lectures from text
            const metaText = card.textContent;
            const durationMatch = metaText.match(/([\\d.]+)\\s*(total\\s*)?(hours?|hr)/i);
            const duration = durationMatch ? durationMatch[0] : null;
            const lecturesMatch = metaText.match(/(\\d+)\\s*lectures?/i);
            const lectures = lecturesMatch ? lecturesMatch[0] : null;

            // Extract level
            const levels = ['All Levels', 'Beginner', 'Intermediate', 'Expert', 'Advanced'];
            let level = null;
            for (const lvl of levels) {
                if (metaText.includes(lvl)) {
                    level = lvl;
                    break;
                }
            }

            // Check bestseller badge
            const bestsellerEl = card.querySelector(
                '[data-purpose="badge-bestseller"], [class*="bestseller"]'
            );
            const bestseller = bestsellerEl ?
                bestsellerEl.textContent.toLowerCase().includes('bestseller') : false;

            courses.push({
                title, url, instructor, rating, reviews_count,
                price, original_price, duration, lectures, level, bestseller
            });
        } catch (e) {
            // Skip malformed cards
        }
    });

    return courses;
}
"""


class ExtractionService:
    """Extracts course data from page DOM."""

    async def extract_courses(self, page: Page) -> List[ScrapedCourse]:
        """Extract course data directly from page DOM.

        Args:
            page: Playwright page with loaded course listing

        Returns:
            List of scraped courses
        """
        raw_courses = await page.evaluate(EXTRACTION_JS)

        if not raw_courses:
            return []

        courses = []
        for data in raw_courses:
            course = ScrapedCourse.from_dict(data)
            if course.is_valid:
                courses.append(course)

        return courses

    def deduplicate(self, courses: List[ScrapedCourse]) -> List[ScrapedCourse]:
        """Remove duplicate courses by title.

        Args:
            courses: List of courses to deduplicate

        Returns:
            List with duplicates removed
        """
        seen = set()
        unique = []

        for course in courses:
            if course.title and course.title not in seen:
                seen.add(course.title)
                unique.append(course)

        return unique
