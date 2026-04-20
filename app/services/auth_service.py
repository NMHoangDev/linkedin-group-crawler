"""Authentication service for LinkedIn session management."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import Error, TimeoutError, sync_playwright

from app.config import settings
from app.utils.file_utils import ensure_directory
from app.utils.logger import get_logger


logger = get_logger(__name__)


def _is_login_verified(current_url: str) -> bool:
    """Check if current URL indicates an authenticated LinkedIn session."""

    normalized = (current_url or "").lower()
    return any(part in normalized for part in ["/feed", "/groups", "/mynetwork", "/jobs"])


def login_and_save_session(force_relogin: bool = False) -> Path:
    """Login to LinkedIn and persist Playwright storage state."""

    if not settings.linkedin_email or not settings.linkedin_password:
        raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in environment variables")

    state_path = settings.state_path
    ensure_directory(state_path.parent)

    if state_path.exists() and not force_relogin:
        logger.info("LinkedIn state file already exists at %s", state_path)
        return state_path

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=settings.headless)
        context = browser.new_context()
        page = context.new_page()

        try:
            logger.info("Opening LinkedIn login page")
            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=60000)
            page.fill('input[name="session_key"]', settings.linkedin_email)
            page.fill('input[name="session_password"]', settings.linkedin_password)
            page.click('button[type="submit"]')

            try:
                page.wait_for_url("**/feed/**", timeout=30000)
            except TimeoutError:
                logger.warning("Automatic login confirmation timed out; LinkedIn may require checkpoint/captcha resolution")

                if settings.headless:
                    raise RuntimeError(
                        "LinkedIn requires manual verification. Set HEADLESS=false and call POST /login again."
                    )

                logger.info("Opening Playwright inspector for manual checkpoint/captcha handling")
                page.pause()

            if not _is_login_verified(page.url):
                raise RuntimeError(
                    "LinkedIn login was not verified. Resolve checkpoint/captcha and retry POST /login."
                )

            context.storage_state(path=str(state_path))
            logger.info("Saved LinkedIn storage state to %s", state_path)
            return state_path
        except Error as exc:
            logger.exception("LinkedIn login failed")
            raise RuntimeError(f"LinkedIn login failed: {exc}") from exc
        finally:
            context.close()
            browser.close()
