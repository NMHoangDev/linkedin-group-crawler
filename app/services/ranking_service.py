"""Ranking and post filtering logic."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.utils.datetime_utils import is_same_day, normalize_relative_time, parse_target_date


def compute_score(post: dict[str, Any]) -> int:
    """Compute post score from engagement values."""

    return int(post.get("likes", 0)) + int(post.get("comments", 0)) + int(post.get("reposts", 0))


def enrich_and_filter_posts(
    posts: list[dict[str, Any]],
    target_date: str | None,
    crawl_time: datetime,
) -> tuple[list[dict[str, Any]], datetime.date]:
    """Normalize timestamps, compute score, and keep posts matching the target day."""

    target_day = parse_target_date(target_date, crawl_time)
    filtered_posts: list[dict[str, Any]] = []

    for post in posts:
        normalized_dt = normalize_relative_time(post.get("posted_at_raw", ""), crawl_time)
        post["posted_at"] = normalized_dt.isoformat() if normalized_dt else None
        post["score"] = compute_score(post)
        if normalized_dt and is_same_day(normalized_dt, target_day):
            filtered_posts.append(post)

    return filtered_posts, target_day


def pick_top_post(posts: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Pick the top post using score, then likes as tie-breaker."""

    if not posts:
        return None
    return max(posts, key=lambda post: (post.get("score", 0), post.get("likes", 0)))
