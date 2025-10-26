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


def apply_war_defaults(war: Dict[str, Any]) -> bool:
    """Apply new default fields to war objects for backward compatibility.

    Returns True if any fields were added/modified.
    """
    mutated = False

    # Stats tracking
    if "stats" not in war:
        war["stats"] = {
            "attacker": {"exosphere": 0, "naval": 0, "military": 0},
            "defender": {"exosphere": 0, "naval": 0, "military": 0}
        }
        mutated = True

    # Theater (cosmetic label)
    if "theater" not in war:
        war["theater"] = "land"
        mutated = True

    # Modifiers tracking
    if "modifiers" not in war:
        war["modifiers"] = {
            "attacker": [],
            "defender": []
        }
        mutated = True

    # Dual-track momentum
    if "tactical_momentum" not in war:
        # Migrate old momentum if it exists
        war["tactical_momentum"] = war.get("momentum", 0)
        mutated = True

    if "strategic_momentum" not in war:
        war["strategic_momentum"] = {
            "attacker": 0,
            "defender": 0
        }
        mutated = True

    # Resolution mode
    if "resolution_mode" not in war:
        war["resolution_mode"] = "gm_driven"
        mutated = True

    if "resolution_cooldown_hours" not in war:
        war["resolution_cooldown_hours"] = 12
        mutated = True

    if "last_resolution_time" not in war:
        war["last_resolution_time"] = None
        mutated = True

    # Pending actions for player-driven wars
    if "pending_actions" not in war:
        war["pending_actions"] = {
            "attacker": None,
            "defender": None
        }
        mutated = True

    # NPC AI configuration
    if "npc_config" not in war:
        war["npc_config"] = {
            "enabled": False,
            "side": None,
            "archetype": "nato",
            "tech_level": "modern",
            "personality": "balanced",
            "base_power": 50,
            "learning_data": {}
        }
        mutated = True

    # Migrate old NPC fields to new structure if they exist
    if war.get("npc_controlled") is True and war["npc_config"]["enabled"] is False:
        war["npc_config"]["enabled"] = True
        war["npc_config"]["side"] = war.get("npc_side")
        war["npc_config"]["personality"] = war.get("npc_ai_personality", "balanced")
        war["npc_config"]["tech_level"] = war.get("npc_tech_level", "modern")
        war["npc_config"]["archetype"] = war.get("npc_archetype", "nato")
        mutated = True

    # Clean up old NPC fields
    old_npc_fields = [
        "npc_controlled", "npc_side", "npc_ai_personality",
        "npc_tech_level", "npc_archetype", "npc_faction_name", "npc_learning_enabled"
    ]
    for field in old_npc_fields:
        if field in war:
            del war[field]
            mutated = True

    return mutated
