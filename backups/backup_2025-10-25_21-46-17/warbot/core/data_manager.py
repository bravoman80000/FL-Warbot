"""Persistent storage helpers for war data."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_ROOT = Path(
    os.getenv(
        "WAR_DATA_DIR",
        Path(__file__).resolve().parent.parent / "data",
    )
)
DATA_FILE = DATA_ROOT / "wars.json"


def _ensure_data_file() -> None:
    """Guarantee the data directory and file exist."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if not DATA_FILE.exists():
        DATA_FILE.write_text("[]", encoding="utf-8")


def load_wars() -> List[Dict[str, Any]]:
    """Load wars from disk, returning an empty list on failure."""
    _ensure_data_file()
    try:
        with DATA_FILE.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(payload, list):
        return []
    return payload


def save_wars(wars: List[Dict[str, Any]]) -> None:
    """Persist wars to disk."""
    _ensure_data_file()
    with DATA_FILE.open("w", encoding="utf-8") as fp:
        json.dump(wars, fp, indent=2, ensure_ascii=True)


def find_war_by_id(wars: List[Dict[str, Any]], war_id: int) -> Optional[Dict[str, Any]]:
    """Locate a war dict by its numeric ID."""
    for war in wars:
        if war.get("id") == war_id:
            return war
    return None
