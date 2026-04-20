"""API routes for LinkedIn group crawler."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.config import BASE_DIR, settings
from app.schemas.request_models import CrawlGroupRequest, LoginRequest
from app.schemas.response_models import BaseResponse, CrawlDataResponse, CrawlResponse, LoginResponse, TopPostResponse
from app.services.auth_service import login_and_save_session
from app.services.crawler_service import open_group_and_collect_posts
from app.services.ranking_service import enrich_and_filter_posts, pick_top_post
from app.utils.logger import get_logger


router = APIRouter()
logger = get_logger(__name__)


def verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Optionally protect endpoints with an API key."""

    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


@router.get("/health", response_model=BaseResponse)
def health_check() -> BaseResponse:
    """Health check endpoint."""

    return BaseResponse(success=True, message="Service is healthy")


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest | None = None) -> LoginResponse:
    """Login to LinkedIn and store browser session state."""

    try:
        state_path = login_and_save_session(force_relogin=payload.force_relogin if payload else False)
        return LoginResponse(
            success=True,
            message="LinkedIn session saved successfully",
            state_path=state_path.relative_to(BASE_DIR).as_posix(),
        )
    except Exception as exc:
        logger.exception("Login endpoint failed")
        return LoginResponse(success=False, message=str(exc), state_path=None)


@router.post("/crawl-linkedin-group", response_model=CrawlResponse, dependencies=[Depends(verify_api_key)])
def crawl_linkedin_group(payload: CrawlGroupRequest) -> CrawlResponse:
    """Crawl a LinkedIn group and return the top post of the target day."""

    try:
        crawl_result = open_group_and_collect_posts(
            group_url=payload.group_url,
            max_items=payload.max_items,
        )
        filtered_posts, target_day = enrich_and_filter_posts(
            posts=crawl_result["posts"],
            target_date=payload.target_date,
            crawl_time=crawl_result["crawl_time"],
        )
        top_post = pick_top_post(filtered_posts)

        if crawl_result["total_posts_scraped"] == 0:
            return CrawlResponse(success=False, message="No posts found on the LinkedIn group page", data=None)

        response_data = CrawlDataResponse(
            group_url=payload.group_url,
            target_date=target_day.isoformat(),
            total_posts_scraped=crawl_result["total_posts_scraped"],
            total_posts_in_target_date=len(filtered_posts),
            top_post=TopPostResponse(**top_post) if top_post else None,
        )
        return CrawlResponse(success=True, message="Crawl completed successfully", data=response_data)
    except Exception as exc:
        logger.exception("Crawl endpoint failed")
        return CrawlResponse(success=False, message=str(exc), data=None)
