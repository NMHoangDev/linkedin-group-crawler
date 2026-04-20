"""Application settings and environment loading."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(slots=True)
class Settings:
    """Typed settings loaded from environment variables."""

    linkedin_email: str = os.getenv("LINKEDIN_EMAIL", "")
    linkedin_password: str = os.getenv("LINKEDIN_PASSWORD", "")
    headless: bool = _parse_bool(os.getenv("HEADLESS"), default=False)
    state_path: Path = BASE_DIR / os.getenv("STATE_PATH", "storage/linkedin_state.json")
    default_scroll_times: int = int(os.getenv("DEFAULT_SCROLL_TIMES", "8"))
    default_scroll_delay_ms: int = int(os.getenv("DEFAULT_SCROLL_DELAY_MS", "2000"))
    default_max_items: int = int(os.getenv("DEFAULT_MAX_ITEMS", "50"))
    api_key: str = os.getenv("API_KEY", "")
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    raw_data_dir: Path = BASE_DIR / "data" / "raw"
    output_data_dir: Path = BASE_DIR / "data" / "output"


settings = Settings()
