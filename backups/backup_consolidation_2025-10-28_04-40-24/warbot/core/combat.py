"""Combat resolution logic for wars."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def calculate_modifiers(
    war: Dict[str, Any], side: str, main_action: str, minor_action: str
) -> Tuple[List[Tuple[str, int]], int]:
    """Auto-calculate all modifiers for a side in combat.

    Returns:
        Tuple of (modifier_list, total_modifier)
        modifier_list is [(name, value), ...]
    """
    mods: List[Tuple[str, int]] = []
    total = 0

    # 1. Stat advantages (based on theater)
    stat_mod = _calculate_stat_advantage(war, side, war.get("theater", "land"))
    if stat_mod != 0:
        theater_name = war.get("theater", "land").title()
        mods.append((f"Stat Advantage ({theater_name})", stat_mod))
        total += stat_mod

    # 2. Permanent/temporary modifiers
    for mod in war.get("modifiers", {}).get(side, []):
        mods.append((mod["name"], mod["value"]))
        total += mod["value"]

    # 3. Main action bonuses
    if main_action == "defend":
        mods.append(("Defense Stance", 2))
        total += 2

    # 4. Minor action bonuses
    if minor_action == "prepare_attack":
        mods.append(("Prepared Attack", 1))
        total += 1
    elif minor_action == "sabotage":
        # Sabotage is applied to enemy, handled separately
        pass
    elif minor_action == "fortify_defense":
        # This reduces damage, doesn't affect roll
        pass
    elif minor_action == "prepare_super_unit":
        # Enables super unit next turn
        pass

    # 5. Tactical momentum
    tactical = war.get("tactical_momentum", 0)
    if tactical != 0:
        momentum_side = "attacker" if tactical > 0 else "defender"
        if momentum_side == side:
            mods.append(("Tactical Momentum", abs(tactical)))
            total += abs(tactical)

    return mods, total


def _calculate_stat_advantage(war: Dict[str, Any], side: str, theater: str) -> int:
    """Calculate stat advantage modifier based on theater and stats."""
    stat_key = {
        "space": "exosphere",
        "naval": "naval",
        "land": "military",
        "combined": "military"  # Combined arms uses military
    }.get(theater, "military")

    my_stat = war.get("stats", {}).get(side, {}).get(stat_key, 0)
    enemy_side = "defender" if side == "attacker" else "attacker"
    enemy_stat = war.get("stats", {}).get(enemy_side, {}).get(stat_key, 0)

    if enemy_stat == 0:
        # Can't divide by zero, no advantage
        return 0

    ratio = my_stat / enemy_stat

    # Based on your war rules:
    # 250%+ -> +3, 150%+ -> +2, 75%+ -> +1
    if ratio >= 2.5:
        return 3
    elif ratio >= 1.5:
        return 2
    elif ratio >= 0.75:
        return 1
    else:
        return 0


def apply_sabotage_to_enemy(
    war: Dict[str, Any], side: str, enemy_mods: List[Tuple[str, int]], enemy_total: int
) -> Tuple[List[Tuple[str, int]], int]:
    """Check if side used sabotage and apply -1 to enemy."""
    # Check if any modifier on this side is a sabotage minor action
    # (In practice, we'll track this differently, but for now...)
    # This is called after calculating enemy mods, so we just add the penalty
    enemy_mods.append(("Enemy Sabotage", -1))
    enemy_total -= 1
    return enemy_mods, enemy_total


def calculate_damage_from_margin(margin: int, strategic_momentum: int) -> int:
    """Calculate warbar damage based on victory margin and strategic momentum.

    Args:
        margin: Difference between winner and loser roll results
        strategic_momentum: Winner's strategic momentum (0-10)

    Returns:
        Final damage to apply to warbar
    """
    # Base damage from margin
    if margin <= 5:
        base = 5  # Narrow victory
    elif margin <= 10:
        base = 10  # Marginal victory
    elif margin <= 15:
        base = 15  # Clear victory
    else:
        base = 20  # Decisive victory

    # Apply strategic momentum multiplier
    multiplier = 1.0 + (strategic_momentum / 10)
    return int(base * multiplier)


def cleanup_expired_modifiers(war: Dict[str, Any]) -> None:
    """Remove expired modifiers from both sides.

    Modifiers with duration "next_resolution" are removed.
    Modifiers with duration "X_turns" have their turn counter decremented.
    """
    for side in ("attacker", "defender"):
        if "modifiers" not in war:
            war["modifiers"] = {"attacker": [], "defender": []}

        remaining = []
        for mod in war["modifiers"][side]:
            duration = mod.get("duration", "permanent")

            if duration == "next_resolution":
                # This modifier expires now
                continue
            elif duration.endswith("_turns"):
                # Decrement turn counter
                try:
                    turns = int(duration.split("_")[0])
                    turns -= 1
                    if turns <= 0:
                        # Expired
                        continue
                    # Update duration
                    mod["duration"] = f"{turns}_turns"
                    remaining.append(mod)
                except (ValueError, IndexError):
                    # Malformed duration, keep as-is
                    remaining.append(mod)
            else:
                # Permanent or unknown duration, keep
                remaining.append(mod)

        war["modifiers"][side] = remaining
