"""Migration utilities for war data structure changes.

Handles migration from old stat-based system to new theater/subhp system.
"""

from __future__ import annotations

from typing import Any, Dict, List
import logging

log = logging.getLogger("warbot.migration")


def migrate_war_to_new_system(war: Dict[str, Any]) -> bool:
    """Migrate a war from old stat/theater system to new custom theater system.

    Args:
        war: War dictionary to migrate

    Returns:
        True if migration was performed, False if already migrated
    """
    migrated = False

    # Remove old stats if they exist
    if "stats" in war:
        log.info(f"Migrating war #{war.get('id')} - removing old stats system")
        del war["stats"]
        migrated = True

    # Remove old theater label if it exists
    if "theater" in war and isinstance(war["theater"], str):
        log.info(f"Migrating war #{war.get('id')} - removing old theater label: {war['theater']}")
        del war["theater"]
        migrated = True

    # Initialize new fields (handled by apply_war_defaults, but we log it)
    if migrated:
        log.info(f"War #{war.get('id')} migrated to new system (theaters: {len(war.get('theaters', []))}, subhps: {len(war.get('attacker_subhps', []))} + {len(war.get('defender_subhps', []))})")

    return migrated


def migrate_all_wars(wars: List[Dict[str, Any]]) -> int:
    """Migrate all wars in the list.

    Args:
        wars: List of war dictionaries

    Returns:
        Number of wars migrated
    """
    count = 0
    for war in wars:
        if migrate_war_to_new_system(war):
            count += 1

    if count > 0:
        log.info(f"Migration complete: {count} wars migrated to new system")
    else:
        log.info("No wars needed migration")

    return count


def validate_war_data(war: Dict[str, Any]) -> List[str]:
    """Validate a war dictionary for data integrity.

    Args:
        war: War dictionary to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Check required fields
    required_fields = ["id", "name", "attacker", "defender", "warbar"]
    for field in required_fields:
        if field not in war:
            errors.append(f"Missing required field: {field}")

    # Check theaters structure
    if "theaters" in war:
        if not isinstance(war["theaters"], list):
            errors.append("theaters must be a list")
        else:
            for i, theater in enumerate(war["theaters"]):
                if not isinstance(theater, dict):
                    errors.append(f"Theater {i} is not a dictionary")
                    continue

                required_theater_fields = ["id", "name", "max_value", "current_value", "status"]
                for field in required_theater_fields:
                    if field not in theater:
                        errors.append(f"Theater {i} missing field: {field}")

    # Check sub-HPs structure
    for side in ["attacker", "defender"]:
        key = f"{side}_subhps"
        if key in war:
            if not isinstance(war[key], list):
                errors.append(f"{key} must be a list")
            else:
                for i, subhp in enumerate(war[key]):
                    if not isinstance(subhp, dict):
                        errors.append(f"{side} sub-HP {i} is not a dictionary")
                        continue

                    required_subhp_fields = ["id", "name", "max_hp", "current_hp", "status"]
                    for field in required_subhp_fields:
                        if field not in subhp:
                            errors.append(f"{side} sub-HP {i} missing field: {field}")

    # Validate no old fields exist
    deprecated_fields = ["stats", "theater"]
    for field in deprecated_fields:
        if field in war:
            errors.append(f"Deprecated field still present: {field} (migration not complete)")

    return errors
