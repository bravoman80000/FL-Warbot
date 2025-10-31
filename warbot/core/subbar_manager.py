"""Unified sub-bar management system.

Handles both:
1. Theaters - Sub-bars for tracking war fronts (Pennsylvania, Gulf, etc.)
2. Sub-HPs - Sub-bars for tracking units/fleets/squads in Attrition Mode

Both systems use identical damage distribution logic.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Tuple


def add_theater(war: Dict[str, Any], name: str, max_value: int) -> int:
    """Add a custom theater to track a war front.

    Args:
        war: War dictionary
        name: Theater name (e.g., "Pennsylvania Theater")
        max_value: Max HP for this theater

    Returns:
        Theater ID
    """
    if "theaters" not in war:
        war["theaters"] = []

    # Generate unique ID
    existing_ids = [t.get("id", 0) for t in war["theaters"]]
    new_id = max(existing_ids, default=0) + 1

    theater = {
        "id": new_id,
        "name": name,
        "max_value": max_value,
        "current_value": 0,  # Starts at neutral
        "status": "active",  # or "closed"
        "side_captured": None  # "attacker", "defender", or None
    }

    war["theaters"].append(theater)
    return new_id


def add_subhp(war: Dict[str, Any], side: Literal["attacker", "defender"], name: str, max_hp: int) -> int:
    """Add a sub-HP to track a fleet/army/squad in Attrition Mode.

    Args:
        war: War dictionary
        side: Which side (attacker or defender)
        name: Unit name (e.g., "1st Fleet", "Alpha Squad")
        max_hp: Max HP for this unit

    Returns:
        Sub-HP ID
    """
    key = f"{side}_subhps"
    if key not in war:
        war[key] = []

    # Generate unique ID
    existing_ids = [s.get("id", 0) for s in war[key]]
    new_id = max(existing_ids, default=0) + 1

    subhp = {
        "id": new_id,
        "name": name,
        "max_hp": max_hp,
        "current_hp": max_hp,  # Starts at full health
        "status": "active"  # or "neutralized"
    }

    war[key].append(subhp)
    return new_id


def remove_theater(war: Dict[str, Any], theater_id: int) -> Optional[Dict[str, Any]]:
    """Remove a theater and return its data.

    Args:
        war: War dictionary
        theater_id: Theater to remove

    Returns:
        Removed theater data, or None if not found
    """
    theaters = war.get("theaters", [])
    for i, theater in enumerate(theaters):
        if theater.get("id") == theater_id:
            removed = theaters.pop(i)
            # Recalculate unassigned
            _recalculate_theater_unassigned(war)
            return removed
    return None


def remove_subhp(war: Dict[str, Any], side: Literal["attacker", "defender"], subhp_id: int) -> Optional[Dict[str, Any]]:
    """Remove a sub-HP and return its data.

    Args:
        war: War dictionary
        side: Which side
        subhp_id: Sub-HP to remove

    Returns:
        Removed sub-HP data, or None if not found
    """
    key = f"{side}_subhps"
    subhps = war.get(key, [])
    for i, subhp in enumerate(subhps):
        if subhp.get("id") == subhp_id:
            removed = subhps.pop(i)
            # Recalculate unassigned
            _recalculate_subhp_unassigned(war, side)
            return removed
    return None


def find_theater_by_id(war: Dict[str, Any], theater_id: int) -> Optional[Dict[str, Any]]:
    """Find a theater by ID.

    Args:
        war: War dictionary
        theater_id: Theater to find

    Returns:
        Theater data, or None if not found
    """
    theaters = war.get("theaters", [])
    for theater in theaters:
        if theater.get("id") == theater_id:
            return theater
    return None


def find_subhp_by_id(war: Dict[str, Any], side: Literal["attacker", "defender"], subhp_id: int) -> Optional[Dict[str, Any]]:
    """Find a sub-HP by ID.

    Args:
        war: War dictionary
        side: Which side
        subhp_id: Sub-HP to find

    Returns:
        Sub-HP data, or None if not found
    """
    key = f"{side}_subhps"
    subhps = war.get(key, [])
    for subhp in subhps:
        if subhp.get("id") == subhp_id:
            return subhp
    return None


def close_theater(war: Dict[str, Any], theater_id: int, side: Literal["attacker", "defender"]) -> bool:
    """Close a theater and mark it as captured.

    Args:
        war: War dictionary
        theater_id: Theater to close
        side: Which side captured it

    Returns:
        True if successful, False if theater not found
    """
    theater = find_theater_by_id(war, theater_id)
    if not theater:
        return False

    theater["status"] = "closed"
    theater["side_captured"] = side
    return True


def reopen_theater(war: Dict[str, Any], theater_id: int) -> bool:
    """Reopen a closed theater and reset it to neutral.

    Args:
        war: War dictionary
        theater_id: Theater to reopen

    Returns:
        True if successful, False if theater not found
    """
    theater = find_theater_by_id(war, theater_id)
    if not theater:
        return False

    theater["status"] = "active"
    theater["side_captured"] = None
    theater["current_value"] = 0  # Reset to neutral
    return True


def apply_theater_damage(war: Dict[str, Any], theater_id: int, damage: int, winner: Literal["attacker", "defender"]) -> bool:
    """Apply damage to a specific theater.

    Args:
        war: War dictionary
        theater_id: Theater to damage
        damage: Amount of damage (positive number)
        winner: Which side won (determines direction)

    Returns:
        True if successful, False if theater not found or closed
    """
    theater = find_theater_by_id(war, theater_id)
    if not theater or theater["status"] == "closed":
        return False

    max_val = theater["max_value"]

    if winner == "attacker":
        theater["current_value"] += damage
        theater["current_value"] = min(theater["current_value"], max_val)
    else:  # defender
        theater["current_value"] -= damage
        theater["current_value"] = max(theater["current_value"], -max_val)

    # Check if theater reached limit
    if abs(theater["current_value"]) >= max_val:
        theater["status"] = "closed"
        theater["side_captured"] = winner

    # Update main warbar
    _sync_warbar_from_theaters(war)
    return True


def apply_subhp_damage(war: Dict[str, Any], side: Literal["attacker", "defender"], subhp_id: int, damage: int) -> bool:
    """Apply damage to a specific sub-HP.

    Args:
        war: War dictionary
        side: Which side
        subhp_id: Sub-HP to damage
        damage: Amount of damage (positive number)

    Returns:
        True if successful, False if sub-HP not found or neutralized
    """
    subhp = find_subhp_by_id(war, side, subhp_id)
    if not subhp or subhp["status"] == "neutralized":
        return False

    subhp["current_hp"] -= damage
    subhp["current_hp"] = max(subhp["current_hp"], 0)

    # Check if neutralized
    if subhp["current_hp"] == 0:
        subhp["status"] = "neutralized"

    # Update main HP
    health_key = f"{side}_health"
    war[health_key] = war.get(health_key, 0) - damage
    war[health_key] = max(war[health_key], 0)

    return True


def apply_subhp_heal(war: Dict[str, Any], side: Literal["attacker", "defender"], subhp_id: int, heal: int) -> bool:
    """Heal a specific sub-HP.

    Args:
        war: War dictionary
        side: Which side
        subhp_id: Sub-HP to heal
        heal: Amount to heal (positive number)

    Returns:
        True if successful, False if sub-HP not found
    """
    subhp = find_subhp_by_id(war, side, subhp_id)
    if not subhp:
        return False

    subhp["current_hp"] += heal
    subhp["current_hp"] = min(subhp["current_hp"], subhp["max_hp"])

    # Restore from neutralized if HP > 0
    if subhp["current_hp"] > 0 and subhp["status"] == "neutralized":
        subhp["status"] = "active"

    # Update main HP
    health_key = f"{side}_health"
    max_health_key = f"{side}_max_health"
    war[health_key] = min(war.get(health_key, 0) + heal, war.get(max_health_key, 100))

    return True


def apply_general_damage_to_theaters(war: Dict[str, Any], damage: int, winner: Literal["attacker", "defender", "stalemate"]) -> None:
    """Apply general damage - consumes unassigned warbar first, then spills to theaters.

    Args:
        war: War dictionary
        damage: Amount of damage (positive number)
        winner: Which side won (determines direction)
    """
    if winner == "stalemate":
        return  # No damage on stalemate

    # Initialize unassigned if not exists
    if "theater_unassigned" not in war:
        war["theater_unassigned"] = war.get("warbar", 0)

    unassigned = war["theater_unassigned"]

    if winner == "attacker":
        # Attacker damage flows positive
        if unassigned < 0:
            # Consume negative unassigned first
            consumed = min(damage, abs(unassigned))
            war["theater_unassigned"] += consumed
            damage -= consumed

        # Spill remaining to theaters
        if damage > 0:
            war["theater_unassigned"] += damage
            _spill_damage_to_theaters(war, damage, "attacker")
    else:  # defender
        # Defender damage flows negative
        if unassigned > 0:
            # Consume positive unassigned first
            consumed = min(damage, abs(unassigned))
            war["theater_unassigned"] -= consumed
            damage -= consumed

        # Spill remaining to theaters
        if damage > 0:
            war["theater_unassigned"] -= damage
            _spill_damage_to_theaters(war, damage, "defender")

    # Update main warbar
    _sync_warbar_from_theaters(war)


def apply_general_damage_to_subhps(war: Dict[str, Any], side: Literal["attacker", "defender"], damage: int) -> None:
    """Apply general damage to a side - consumes unassigned HP first, then distributes to sub-HPs.

    Args:
        war: War dictionary
        side: Which side is taking damage
        damage: Amount of damage (positive number)
    """
    unassigned_key = f"{side}_unassigned_hp"

    # Initialize unassigned if not exists
    if unassigned_key not in war:
        _recalculate_subhp_unassigned(war, side)

    unassigned = war.get(unassigned_key, 0)

    # Consume unassigned first
    if unassigned > 0:
        consumed = min(damage, unassigned)
        war[unassigned_key] -= consumed
        damage -= consumed

    # Distribute remaining damage evenly to active sub-HPs
    if damage > 0:
        _distribute_damage_to_subhps(war, side, damage)

    # Update main HP
    health_key = f"{side}_health"
    war[health_key] = war.get(health_key, 0) - damage
    war[health_key] = max(war[health_key], 0)


def _spill_damage_to_theaters(war: Dict[str, Any], damage: int, winner: Literal["attacker", "defender"]) -> None:
    """Distribute damage proportionally to active theaters.

    Args:
        war: War dictionary
        damage: Remaining damage to distribute
        winner: Which side is dealing damage
    """
    theaters = [t for t in war.get("theaters", []) if t["status"] == "active"]
    if not theaters:
        return

    # Distribute evenly
    damage_per_theater = damage // len(theaters)
    remainder = damage % len(theaters)

    for i, theater in enumerate(theaters):
        theater_damage = damage_per_theater + (1 if i < remainder else 0)

        if winner == "attacker":
            theater["current_value"] += theater_damage
            theater["current_value"] = min(theater["current_value"], theater["max_value"])
        else:
            theater["current_value"] -= theater_damage
            theater["current_value"] = max(theater["current_value"], -theater["max_value"])

        # Check if captured
        if abs(theater["current_value"]) >= theater["max_value"]:
            theater["status"] = "closed"
            theater["side_captured"] = winner


def _distribute_damage_to_subhps(war: Dict[str, Any], side: Literal["attacker", "defender"], damage: int) -> None:
    """Distribute damage evenly to active sub-HPs.

    Args:
        war: War dictionary
        side: Which side is taking damage
        damage: Damage to distribute
    """
    key = f"{side}_subhps"
    subhps = [s for s in war.get(key, []) if s["status"] == "active"]

    if not subhps:
        return

    # Distribute evenly
    damage_per_subhp = damage // len(subhps)
    remainder = damage % len(subhps)

    for i, subhp in enumerate(subhps):
        subhp_damage = damage_per_subhp + (1 if i < remainder else 0)

        subhp["current_hp"] -= subhp_damage
        subhp["current_hp"] = max(subhp["current_hp"], 0)

        # Check if neutralized
        if subhp["current_hp"] == 0:
            subhp["status"] = "neutralized"


def _sync_warbar_from_theaters(war: Dict[str, Any]) -> None:
    """Recalculate main warbar from theater values + unassigned.

    Args:
        war: War dictionary
    """
    total = war.get("theater_unassigned", 0)

    for theater in war.get("theaters", []):
        total += theater.get("current_value", 0)

    war["warbar"] = total


def _recalculate_theater_unassigned(war: Dict[str, Any]) -> None:
    """Recalculate unassigned warbar after theaters change.

    Args:
        war: War dictionary
    """
    total_theater_value = sum(t.get("current_value", 0) for t in war.get("theaters", []))
    war["theater_unassigned"] = war.get("warbar", 0) - total_theater_value


def _recalculate_subhp_unassigned(war: Dict[str, Any], side: Literal["attacker", "defender"]) -> None:
    """Recalculate unassigned HP after sub-HPs change.

    Args:
        war: War dictionary
        side: Which side to recalculate
    """
    key = f"{side}_subhps"
    health_key = f"{side}_health"
    unassigned_key = f"{side}_unassigned_hp"

    total_subhp = sum(s.get("current_hp", 0) for s in war.get(key, []))
    main_hp = war.get(health_key, 0)

    war[unassigned_key] = main_hp - total_subhp


def calculate_total_warbar(war: Dict[str, Any]) -> int:
    """Calculate total warbar from all theater values + unassigned.

    Args:
        war: War dictionary

    Returns:
        Total warbar value
    """
    total = war.get("theater_unassigned", 0)
    for theater in war.get("theaters", []):
        total += theater.get("current_value", 0)
    return total


def get_active_theaters(war: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get list of active (non-closed) theaters.

    Args:
        war: War dictionary

    Returns:
        List of active theaters
    """
    return [t for t in war.get("theaters", []) if t["status"] == "active"]


def get_active_subhps(war: Dict[str, Any], side: Literal["attacker", "defender"]) -> List[Dict[str, Any]]:
    """Get list of active (non-neutralized) sub-HPs.

    Args:
        war: War dictionary
        side: Which side

    Returns:
        List of active sub-HPs
    """
    key = f"{side}_subhps"
    return [s for s in war.get(key, []) if s["status"] == "active"]
