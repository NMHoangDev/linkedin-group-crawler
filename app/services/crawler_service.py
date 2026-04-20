"""Playwright crawler service for LinkedIn groups."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from playwright.sync_api import Error, Page, sync_playwright

from app.config import settings
from app.services.parser_service import parse_post_locator
from app.utils.file_utils import ensure_directory, save_text_file
from app.utils.logger import get_logger


logger = get_logger(__name__)

# LinkedIn frequently changes feed/group DOM; keep fallback selectors to reduce breakage.
POST_SELECTORS = [
    'div[data-id^="urn:li:activity"]',
    "div.feed-shared-update-v2",
    "div.occludable-update",
]


def _take_error_screenshot(page: Page, filename: str = "error.png") -> str:
    screenshot_path = settings.raw_data_dir / filename
    ensure_directory(screenshot_path.parent)
    page.screenshot(path=str(screenshot_path), full_page=True)
    return str(screenshot_path)


def _locate_post_elements(page: Page):
    """Return the first locator that finds LinkedIn post elements."""

    for selector in POST_SELECTORS:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                logger.info("Using post selector: %s", selector)
                return locator
        except Error:
            logger.debug("Selector check failed for %s", selector, exc_info=True)
    return page.locator(POST_SELECTORS[0])


def open_group_and_collect_posts(
    group_url: str,
    max_items: int | None = None,
    save_raw_html: bool = True,
) -> dict[str, Any]:
    """Open a LinkedIn group page, scroll, and parse post data."""

    if not settings.state_path.exists():
        raise FileNotFoundError(
            f"LinkedIn state file not found at {settings.state_path}. Call POST /login first."
        )

    crawl_time = datetime.now()
    max_items = max_items or settings.default_max_items
    ensure_directory(settings.raw_data_dir)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=settings.headless)
        context = browser.new_context(storage_state=str(settings.state_path))
        page = context.new_page()

        try:
            logger.info("Opening group URL: %s", group_url)
            page.goto(group_url, wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(4000)

            for scroll_index in range(settings.default_scroll_times):
                page.mouse.wheel(0, 3000)
                page.wait_for_timeout(settings.default_scroll_delay_ms)
                locator = _locate_post_elements(page)
                count = locator.count()
                logger.info("Scroll %s/%s collected %s posts", scroll_index + 1, settings.default_scroll_times, count)
                if count >= max_items:
                    break

            locator = _locate_post_elements(page)
            total_found = min(locator.count(), max_items)
            logger.info("Preparing to parse %s posts", total_found)

            if save_raw_html:
                html_path = settings.raw_data_dir / "last_group_page.html"
                save_text_file(html_path, page.content())

            posts: list[dict[str, Any]] = []
            for index in range(total_found):
                item = locator.nth(index)
                parsed = parse_post_locator(item)
                if parsed:
                    posts.append(parsed)

            if not posts:
                logger.warning("No posts found on the group page")

            return {
                "crawl_time": crawl_time,
                "group_url": group_url,
                "posts": posts,
                "total_posts_scraped": total_found,
            }
        except Error as exc:
            screenshot_path = _take_error_screenshot(page)
            logger.exception("Crawl failed; screenshot saved to %s", screenshot_path)
            raise RuntimeError(f"Crawl failed: {exc}. Screenshot saved to {screenshot_path}") from exc
        finally:
            context.close()
            browser.close()
