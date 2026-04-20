"""Response models for API endpoints."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """Common response envelope."""

    success: bool
    message: str
    data: Optional[Any] = None


class LoginResponse(BaseResponse):
    """Login response payload."""

    state_path: Optional[str] = None
    session_b64: Optional[str] = None


class TopPostResponse(BaseModel):
    """Normalized top post representation."""

    author: str = ""
    content: str = ""
    posted_at_raw: str = ""
    posted_at: Optional[str] = None
    likes: int = 0
    comments: int = 0
    reposts: int = 0
    score: int = 0
    post_url: str = ""


class CrawlDataResponse(BaseModel):
    """Data section for crawl response."""

    group_url: str
    target_date: str
    total_posts_scraped: int = Field(default=0)
    total_posts_in_target_date: int = Field(default=0)
    top_post: Optional[TopPostResponse] = None


class CrawlResponse(BaseResponse):
    """Crawl endpoint response."""

    data: Optional[CrawlDataResponse] = None
