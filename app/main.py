"""FastAPI application entrypoint."""

from __future__ import annotations

import base64
import json
import os

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.utils.file_utils import ensure_directory, save_json_file
from app.utils.logger import get_logger, setup_logging


setup_logging()
logger = get_logger(__name__)

ensure_directory(settings.raw_data_dir)
ensure_directory(settings.output_data_dir)
ensure_directory(settings.state_path.parent)

app = FastAPI(
    title="LinkedIn Group Crawler API",
    version="1.0.0",
    description="FastAPI service to login, crawl LinkedIn groups, and expose top daily posts for n8n.",
)


@app.on_event("startup")
def restore_session_from_env() -> None:
    """Restore Playwright session from LINKEDIN_SESSION_B64 on app startup."""

    session_b64 = os.getenv("LINKEDIN_SESSION_B64", "").strip()
    if not session_b64:
        return

    try:
        decoded = base64.b64decode(session_b64)
        payload = json.loads(decoded.decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("LINKEDIN_SESSION_B64 must decode to a JSON object")
        if not isinstance(payload.get("cookies"), list):
            raise ValueError('Decoded session missing valid "cookies" list')
        if not isinstance(payload.get("origins"), list):
            raise ValueError('Decoded session missing valid "origins" list')

        save_json_file(settings.state_path, payload)
        logger.info("Restored LinkedIn session from LINKEDIN_SESSION_B64 to %s", settings.state_path)
    except Exception:
        logger.exception("Failed to restore LINKEDIN_SESSION_B64")


app.include_router(router)
