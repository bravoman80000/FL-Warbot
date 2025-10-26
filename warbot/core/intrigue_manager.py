"""Data management for intrigue operations (espionage, sabotage, rebellion, etc.)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .data_manager import DATA_ROOT

INTRIGUE_FILE = DATA_ROOT / "intrigue.json"


def _ensure_intrigue_file() -> None:
    """Ensure intrigue data file exists."""
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if not INTRIGUE_FILE.exists():
        INTRIGUE_FILE.write_text("[]", encoding="utf-8")


def load_operations() -> List[Dict[str, Any]]:
    """Load all intrigue operations from disk."""
    _ensure_intrigue_file()
    try:
        with INTRIGUE_FILE.open("r", encoding="utf-8") as fp:
            payload = json.load(fp)
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(payload, list):
        return []
    return payload


def save_operations(operations: List[Dict[str, Any]]) -> None:
    """Save intrigue operations to disk."""
    _ensure_intrigue_file()
    with INTRIGUE_FILE.open("w", encoding="utf-8") as fp:
        json.dump(operations, fp, indent=2, ensure_ascii=True)


def find_operation_by_id(operations: List[Dict[str, Any]], op_id: int) -> Optional[Dict[str, Any]]:
    """Find an operation by its ID."""
    for op in operations:
        if op.get("id") == op_id:
            return op
    return None


def get_next_operation_id(operations: List[Dict[str, Any]]) -> int:
    """Generate next operation ID."""
    if not operations:
        return 1
    return max(op.get("id", 0) for op in operations) + 1


def create_operation(
    op_type: str,
    operator_faction: str,
    target_faction: str,
    operator_member_id: int,
    guild_id: int,
    channel_id: int,
    description: str,
    **kwargs
) -> Dict[str, Any]:
    """Create a new intrigue operation.

    Args:
        op_type: Type of operation (espionage, sabotage, rebellion, etc.)
        operator_faction: Faction performing the operation
        target_faction: Faction being targeted
        operator_member_id: Discord user ID of operator
        guild_id: Discord guild ID
        channel_id: Discord channel ID for updates
        description: Player-written description of the operation
        **kwargs: Additional operation-specific parameters

    Returns:
        New operation dictionary
    """
    now = datetime.now(timezone.utc).isoformat()

    operation = {
        "id": None,  # Will be set when added to list
        "type": op_type,
        "operator_faction": operator_faction,
        "target_faction": target_faction,
        "operator_member_id": operator_member_id,
        "guild_id": guild_id,
        "channel_id": channel_id,
        "description": description,
        "status": "pending",  # pending, active, success, failed, detected, cancelled
        "created_at": now,
        "resolved_at": None,
        "detection_risk": calculate_detection_risk(op_type, kwargs),
        "detection_rolled": False,
        "detected_by": None,
        "result": None,
        "roll": None,
        "modifiers": [],
        "total": None,
        "difficulty": get_operation_difficulty(op_type, kwargs),
        **kwargs
    }

    return operation


def calculate_detection_risk(op_type: str, params: Dict[str, Any]) -> float:
    """Calculate base detection risk for an operation type.

    Returns value between 0.0 and 1.0 representing percentage chance of detection.
    """
    base_risks = {
        "espionage": 0.15,      # Low risk, subtle
        "sabotage": 0.30,        # Medium risk, obvious damage
        "rebellion": 0.50,       # High risk, public uprising
        "influence": 0.20,       # Low-medium risk, gradual
        "assassination": 0.40,   # Medium-high risk, high profile
        "counterintel": 0.10,    # Low risk, defensive
    }

    base = base_risks.get(op_type, 0.25)

    # Modifier based on operation scale
    scale = params.get("scale", "small")
    scale_mods = {
        "small": -0.05,
        "medium": 0.0,
        "large": 0.10,
        "massive": 0.20,
    }
    base += scale_mods.get(scale, 0.0)

    # Clamp to 0-1 range
    return max(0.0, min(1.0, base))


def get_operation_difficulty(op_type: str, params: Dict[str, Any]) -> int:
    """Get DC (difficulty class) for an operation type.

    Returns target roll needed for success.
    """
    base_dcs = {
        "espionage": 12,         # Moderate difficulty
        "sabotage": 14,          # Harder, requires access
        "rebellion": 16,         # Very hard, needs popular support
        "influence": 13,         # Moderate-hard, gradual process
        "assassination": 18,     # Extremely hard, high security
        "counterintel": 10,      # Easier, defensive advantage
    }

    base = base_dcs.get(op_type, 15)

    # Modifier based on target faction strength (if provided)
    target_strength = params.get("target_strength", "medium")
    strength_mods = {
        "weak": -2,
        "medium": 0,
        "strong": 2,
        "very_strong": 4,
    }
    base += strength_mods.get(target_strength, 0)

    return base


def get_active_operations_by_faction(
    operations: List[Dict[str, Any]], faction: str
) -> List[Dict[str, Any]]:
    """Get all active operations for a faction (both operating and being targeted)."""
    return [
        op for op in operations
        if op.get("status") in ("pending", "active")
        and (op.get("operator_faction") == faction or op.get("target_faction") == faction)
    ]


def get_operations_by_target(
    operations: List[Dict[str, Any]], target_faction: str, status: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Get operations targeting a specific faction, optionally filtered by status."""
    results = [op for op in operations if op.get("target_faction") == target_faction]
    if status:
        results = [op for op in results if op.get("status") == status]
    return results


def check_cooldown(
    operations: List[Dict[str, Any]],
    operator_member_id: int,
    op_type: str,
    cooldown_hours: int = 24
) -> Optional[float]:
    """Check if operator is on cooldown for this operation type.

    Args:
        operations: List of all operations
        operator_member_id: Discord user ID
        op_type: Operation type to check
        cooldown_hours: Hours before can operate again

    Returns:
        None if no cooldown, otherwise hours remaining
    """
    from datetime import datetime, timedelta, timezone

    # Find most recent operation of this type by this operator
    recent_ops = [
        op for op in operations
        if op.get("operator_member_id") == operator_member_id
        and op.get("type") == op_type
        and op.get("resolved_at") is not None
    ]

    if not recent_ops:
        return None

    # Sort by resolved time, get most recent
    recent_ops.sort(key=lambda x: x.get("resolved_at", ""), reverse=True)
    last_op = recent_ops[0]

    try:
        resolved_time = datetime.fromisoformat(last_op["resolved_at"])
        if resolved_time.tzinfo is None:
            resolved_time = resolved_time.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        time_since = (now - resolved_time).total_seconds() / 3600

        if time_since < cooldown_hours:
            return cooldown_hours - time_since
        return None
    except (ValueError, TypeError):
        return None


def apply_operation_effects(operation: Dict[str, Any], target_wars: List[Dict[str, Any]]) -> List[str]:
    """Apply the effects of a successful operation.

    Args:
        operation: The successful operation
        target_wars: List of all wars (may be modified)

    Returns:
        List of effect description strings
    """
    effects = []
    op_type = operation.get("type")
    target_faction = operation.get("target_faction")

    if op_type == "espionage":
        # Espionage reveals information but doesn't modify game state
        effects.append(f"Intelligence gathered on {target_faction}")
        operation["intel_gained"] = {
            "faction_stats": "revealed",
            "war_status": "revealed",
            "ongoing_operations": "revealed",
        }

    elif op_type == "sabotage":
        # Sabotage reduces stats in ongoing wars
        scale = operation.get("scale", "small")
        reduction_map = {"small": 5, "medium": 10, "large": 15, "massive": 20}
        reduction = reduction_map.get(scale, 5)

        target_category = operation.get("target_category", "military")

        for war in target_wars:
            # Check if target faction is in this war
            for side in ("attacker", "defender"):
                if war.get(side) == target_faction:
                    # Reduce the targeted stat
                    current = war.get("stats", {}).get(side, {}).get(target_category, 0)
                    new_value = max(0, current - reduction)
                    war["stats"][side][target_category] = new_value
                    effects.append(
                        f"Sabotage reduced {target_faction}'s {target_category} from {current} to {new_value}"
                    )

    elif op_type == "rebellion":
        # Rebellion creates a temporary modifier or could spawn a war
        effects.append(f"Rebellion incited in {target_faction} territory!")
        operation["rebellion_active"] = True
        # Note: GM would manually create war using /war create if rebellion succeeds

    elif op_type == "influence":
        # Influence spreads ideology/religion
        influence_type = operation.get("influence_type", "political")
        scale = operation.get("scale", "small")
        effects.append(f"{influence_type.title()} influence increased in {target_faction} ({scale} scale)")
        operation["influence_progress"] = scale

    elif op_type == "assassination":
        # Assassination removes a key figure
        target_name = operation.get("target_name", "key figure")
        effects.append(f"Assassination of {target_name} successful!")
        operation["target_eliminated"] = True

    elif op_type == "counterintel":
        # Counterintel disrupts enemy operations
        effects.append(f"Counter-intelligence operation protected against {target_faction}")
        operation["protection_active"] = True

    return effects
