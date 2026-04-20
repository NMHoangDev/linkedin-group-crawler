"""Filesystem helper utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def ensure_directory(path: Path) -> Path:
    """Ensure a directory exists and return it."""

    path.mkdir(parents=True, exist_ok=True)
    return path


def save_json_file(path: Path, data: Any) -> Path:
    """Save JSON data to a file path."""

    ensure_directory(path.parent)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def save_text_file(path: Path, content: str) -> Path:
    """Save text content to a file path."""

    ensure_directory(path.parent)
    path.write_text(content, encoding="utf-8")
    return path
