"""Super Unit management logic."""

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
SUPERUNIT_FILE = DATA_ROOT / "superunits.json"


def _ensure_data_file() -> None:
    """Guarantee the data directory and file exist."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if not SUPERUNIT_FILE.exists():
        SUPERUNIT_FILE.write_text("[]", encoding="utf-8")


def load_super_units() -> List[Dict[str, Any]]:
    """Load super units from disk."""
    _ensure_data_file()
    try:
        with SUPERUNIT_FILE.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(payload, list):
        return []
    return payload


def save_super_units(units: List[Dict[str, Any]]) -> None:
    """Persist super units to disk."""
    _ensure_data_file()
    with SUPERUNIT_FILE.open("w", encoding="utf-8") as fp:
        json.dump(units, fp, indent=2, ensure_ascii=True)


def find_super_unit_by_id(units: List[Dict[str, Any]], unit_id: int) -> Optional[Dict[str, Any]]:
    """Locate a super unit by its numeric ID."""
    for unit in units:
        if unit.get("id") == unit_id:
            return unit
    return None


def calculate_combat_modifier(unit: Dict[str, Any]) -> int:
    """Calculate combat modifier based on intel progress.

    Returns:
        +2 if all intel unlocked (100%)
        0 if half or more unlocked (50-99%)
        -2 if less than half unlocked (0-49%)
    """
    current = unit.get("current_intel", 0)
    maximum = unit.get("max_intel", 1)

    if maximum == 0:
        return 0

    progress = current / maximum

    if progress >= 1.0:
        return 2  # All intel
    elif progress >= 0.5:
        return 0  # Half or more
    else:
        return -2  # Less than half
