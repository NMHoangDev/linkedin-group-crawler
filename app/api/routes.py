"""API routes for LinkedIn group crawler."""

from __future__ import annotations

import base64
import json
import os

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
import httpx

from app.config import BASE_DIR, settings
from app.schemas.request_models import CrawlGroupRequest, LoginRequest
from app.schemas.response_models import BaseResponse, CrawlDataResponse, CrawlResponse, LoginResponse, TopPostResponse
from app.services.auth_service import login_and_save_session
from app.services.crawler_service import open_group_and_collect_posts
from app.services.ranking_service import enrich_and_filter_posts, pick_top_post
from app.utils.file_utils import save_json_file
from app.utils.logger import get_logger


router = APIRouter()
logger = get_logger(__name__)


def _state_path_for_response() -> str:
    """Return a user-friendly state path for API responses."""

    try:
        return settings.state_path.relative_to(BASE_DIR).as_posix()
    except ValueError:
        return str(settings.state_path)


async def _update_render_session_env(session_b64: str) -> bool:
    """Update LINKEDIN_SESSION_B64 on Render using Render API v1."""

    render_api_key = settings.render_api_key or os.getenv("RENDER_API_KEY", "")
    render_service_id = settings.render_service_id or os.getenv("RENDER_SERVICE_ID", "")

    if not render_api_key or not render_service_id:
        logger.warning("Skipping Render env update: missing RENDER_API_KEY or RENDER_SERVICE_ID")
        return False

    url = f"https://api.render.com/v1/services/{render_service_id}/env-vars"
    headers = {
        "Authorization": f"Bearer {render_api_key}",
        "Content-Type": "application/json",
    }
    payload = [{"key": "LINKEDIN_SESSION_B64", "value": session_b64}]

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.put(url, headers=headers, json=payload)
            response.raise_for_status()
        logger.info("Render environment updated successfully for LINKEDIN_SESSION_B64")
        return True
    except Exception:
        logger.exception("Failed to update LINKEDIN_SESSION_B64 on Render")
        return False


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
            state_path=_state_path_for_response(),
        )
    except Exception as exc:
        logger.exception("Login endpoint failed")
        return LoginResponse(success=False, message=str(exc), state_path=None)


@router.post("/upload-session", response_model=LoginResponse, dependencies=[Depends(verify_api_key)])
async def upload_session(request: Request) -> LoginResponse:
    """Upload and persist Playwright storage state using raw JSON body."""

    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ValueError("Request body must be a JSON object")

        cookies = payload.get("cookies")
        origins = payload.get("origins")

        if not isinstance(cookies, list):
            raise ValueError('"cookies" must be a list')
        if not isinstance(origins, list):
            raise ValueError('"origins" must be a list')

        session_json = json.dumps(payload, ensure_ascii=False)
        session_b64 = base64.b64encode(session_json.encode("utf-8")).decode("utf-8")

        save_json_file(settings.state_path, payload)
        logger.info("Uploaded session saved to %s", settings.state_path)
        render_updated = await _update_render_session_env(session_b64)
        return LoginResponse(
            success=True,
            message=f"Session uploaded successfully (render_updated={str(render_updated).lower()})",
            state_path=_state_path_for_response(),
            session_b64=session_b64,
        )
    except Exception as exc:
        logger.exception("Upload session endpoint failed")
        return LoginResponse(success=False, message=str(exc), state_path=None, session_b64=None)


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
@router.get("/debug-screenshot")
def debug_screenshot():
    from fastapi.responses import FileResponse
    import os
    if os.path.exists("/tmp/linkedin_debug.png"):
        return FileResponse("/tmp/linkedin_debug.png")
    return {"error": "No screenshot yet"}