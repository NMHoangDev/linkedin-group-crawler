"""Parsing helpers for LinkedIn post elements."""

from __future__ import annotations

import re
from typing import Any

from playwright.sync_api import Error, Locator

from app.utils.logger import get_logger


logger = get_logger(__name__)

# LinkedIn selectors are intentionally redundant here because class names can change over time.
AUTHOR_SELECTORS = [
    '.update-components-actor__name span[aria-hidden="true"]',
    ".feed-shared-actor__name",
    'a[href*="/in/"] span[aria-hidden="true"]',
]
CONTENT_SELECTORS = [
    ".update-components-text",
    ".feed-shared-text",
    '[data-test-id="main-feed-activity-card__commentary"]',
]
TIME_SELECTORS = [
    ".update-components-actor__sub-description span[aria-hidden='true']",
    ".feed-shared-actor__sub-description",
    'span[aria-label*="ago"]',
]
REACTION_SELECTORS = [
    ".social-details-social-counts__reactions-count",
    'button[aria-label*="reaction"]',
]
COMMENT_SELECTORS = [
    'button[aria-label*="comment"]',
    ".social-details-social-counts__comments button",
]
REPOST_SELECTORS = [
    'button[aria-label*="repost"]',
    'button[aria-label*="share"]',
]
LINK_SELECTORS = [
    'a[href*="/feed/update/"]',
    'a[href*="/posts/"]',
]


def _safe_text(locator: Locator, selectors: list[str], default: str = "") -> str:
    for selector in selectors:
        try:
            element = locator.locator(selector).first
            if element.count() > 0:
                text = element.inner_text(timeout=2000).strip()
                if text:
                    return text
        except Error:
            logger.debug("Could not extract text with selector %s", selector, exc_info=True)
    return default


def _safe_attribute(locator: Locator, selectors: list[str], attribute: str) -> str:
    for selector in selectors:
        try:
            element = locator.locator(selector).first
            if element.count() > 0:
                value = element.get_attribute(attribute, timeout=2000) or ""
                if value:
                    return value
        except Error:
            logger.debug("Could not extract attribute %s with selector %s", attribute, selector, exc_info=True)
    return ""


def extract_number(text: str) -> int:
    """Extract a number from LinkedIn reaction text, supporting K/M suffixes."""

    cleaned = text.replace(",", "").strip().lower()
    if not cleaned:
        return 0

    match = re.search(r"(\d+(?:\.\d+)?)\s*([km]?)", cleaned)
    if not match:
        return 0

    number = float(match.group(1))
    suffix = match.group(2)
    multiplier = 1
    if suffix == "k":
        multiplier = 1_000
    elif suffix == "m":
        multiplier = 1_000_000

    return int(number * multiplier)


def _extract_metric_by_aria(locator: Locator, keyword: str) -> int:
    try:
        candidates = locator.locator(f'button[aria-label*="{keyword}"], span[aria-label*="{keyword}"]')
        for index in range(candidates.count()):
            label = candidates.nth(index).get_attribute("aria-label") or ""
            value = extract_number(label)
            if value:
                return value
    except Error:
        logger.debug("Could not extract metric for keyword %s", keyword, exc_info=True)
    return 0


def parse_post_locator(post_locator: Locator) -> dict[str, Any] | None:
    """Parse a LinkedIn post locator into a normalized dictionary."""

    try:
        author = _safe_text(post_locator, AUTHOR_SELECTORS, default="Unknown author")
        content = _safe_text(post_locator, CONTENT_SELECTORS, default="")
        posted_at_raw = _safe_text(post_locator, TIME_SELECTORS, default="")
        post_url = _safe_attribute(post_locator, LINK_SELECTORS, "href")

        likes_text = _safe_text(post_locator, REACTION_SELECTORS, default="")
        comments_text = _safe_text(post_locator, COMMENT_SELECTORS, default="")
        reposts_text = _safe_text(post_locator, REPOST_SELECTORS, default="")

        likes = extract_number(likes_text) or _extract_metric_by_aria(post_locator, "reaction")
        comments = extract_number(comments_text) or _extract_metric_by_aria(post_locator, "comment")
        reposts = extract_number(reposts_text) or _extract_metric_by_aria(post_locator, "repost")

        return {
            "author": author,
            "content": content,
            "posted_at_raw": posted_at_raw,
            "likes": likes,
            "comments": comments,
            "reposts": reposts,
            "post_url": post_url,
        }
    except Error:
        logger.exception("Failed to parse one post element; skipping it")
        return None
