"""Request models for API endpoints."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    """Optional request body for login endpoint."""

    force_relogin: bool = Field(default=False, description="Ignore existing state and login again.")


class CrawlGroupRequest(BaseModel):
    """Request payload for crawling a LinkedIn group."""

    group_url: str = Field(..., min_length=1, description="LinkedIn group URL.")
    max_items: Optional[int] = Field(default=None, ge=1, le=500)
    target_date: Optional[str] = Field(default=None, description="Target date in YYYY-MM-DD format.")

    @field_validator("group_url")
    @classmethod
    def validate_group_url(cls, value: str) -> str:
        normalized = value.strip()
        if "linkedin.com/groups/" not in normalized:
            raise ValueError("group_url must be a valid LinkedIn Group URL")
        return normalized
