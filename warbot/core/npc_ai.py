"""NPC AI system for PvE war opponents."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

# ========== TECH LEVELS ==========
TECH_LEVELS = {
    "legacy": {
        "name": "Legacy",
        "description": "Cold War-era technology (1960s-1990s)",
        "stat_multiplier": 0.7,
        "examples": "AK-47s, T-72 tanks, early jets, basic radio comms",
    },
    "modern": {
        "name": "Modern",
        "description": "Contemporary military tech (2000s-2020s)",
        "stat_multiplier": 1.0,
        "examples": "M4 carbines, Abrams tanks, drones, digital comms",
    },
    "advanced": {
        "name": "Advanced",
        "description": "Near-future tech (2020s-2100s)",
        "stat_multiplier": 1.2,
        "examples": "Smart weapons, active camo, AI targeting, cyber warfare",
    },
    "cutting_edge": {
        "name": "Cutting Edge",
        "description": "Bleeding-edge 2240 tech",
        "stat_multiplier": 1.4,
        "examples": "Nanoweapons, neural interfaces, orbital strikes, full AI integration",
    },
}

# ========== ARCHETYPES ==========
ARCHETYPES = {
    "nato": {
        "name": "NATO Doctrine",
        "description": "Professional combined-arms force with air superiority focus",
        "stat_weights": {"exosphere": 0.3, "naval": 0.3, "military": 0.4},
        "preferred_main_actions": ["attack", "super_unit"],
        "preferred_minor_actions": ["prepare_attack", "sabotage"],
        "aggression": 0.6,
    },
    "csat": {
        "name": "CSAT Doctrine",
        "description": "Mass mobilization with emphasis on ground forces",
        "stat_weights": {"exosphere": 0.2, "naval": 0.2, "military": 0.6},
        "preferred_main_actions": ["attack", "defend"],
        "preferred_minor_actions": ["fortify_defense", "heal"],
        "aggression": 0.5,
    },
    "guerrilla": {
        "name": "Guerrilla Force",
        "description": "Asymmetric warfare specialists, hit-and-run tactics",
        "stat_weights": {"exosphere": 0.1, "naval": 0.1, "military": 0.8},
        "preferred_main_actions": ["defend"],
        "preferred_minor_actions": ["sabotage", "prepare_attack"],
        "aggression": 0.4,
    },
    "swarm": {
        "name": "Swarm Doctrine",
        "description": "Overwhelming numbers, drone-heavy approach",
        "stat_weights": {"exosphere": 0.4, "naval": 0.2, "military": 0.4},
        "preferred_main_actions": ["attack"],
        "preferred_minor_actions": ["prepare_attack", "sabotage"],
        "aggression": 0.8,
    },
    "elite": {
        "name": "Elite Force",
        "description": "Small, highly-trained professional units",
        "stat_weights": {"exosphere": 0.3, "naval": 0.2, "military": 0.5},
        "preferred_main_actions": ["attack", "super_unit"],
        "preferred_minor_actions": ["prepare_attack", "prepare_super_unit"],
        "aggression": 0.7,
    },
    "defensive_bloc": {
        "name": "Defensive Bloc",
        "description": "Fortification-focused, attrition warfare",
        "stat_weights": {"exosphere": 0.2, "naval": 0.3, "military": 0.5},
        "preferred_main_actions": ["defend"],
        "preferred_minor_actions": ["fortify_defense", "heal"],
        "aggression": 0.3,
    },
    "insurgent": {
        "name": "Insurgent/Rebel Force",
        "description": "Rebellion, terrorism, incited conflicts - unpredictable hit-and-fade tactics",
        "stat_weights": {"exosphere": 0.05, "naval": 0.05, "military": 0.9},
        "preferred_main_actions": ["defend"],
        "preferred_minor_actions": ["sabotage", "prepare_attack"],
        "aggression": 0.6,
    },
}

# ========== PERSONALITIES ==========
PERSONALITIES = {
    "aggressive": {
        "name": "Aggressive",
        "description": "Prefers offensive actions, high risk tolerance",
        "aggression_modifier": 0.3,
        "action_bias": {"attack": 0.7, "defend": 0.2, "super_unit": 0.1},
    },
    "defensive": {
        "name": "Defensive",
        "description": "Prefers defensive posture, low risk tolerance",
        "aggression_modifier": -0.3,
        "action_bias": {"attack": 0.2, "defend": 0.7, "super_unit": 0.1},
    },
    "adaptive": {
        "name": "Adaptive",
        "description": "Adjusts tactics based on tactical momentum",
        "aggression_modifier": 0.0,
        "action_bias": {"attack": 0.4, "defend": 0.4, "super_unit": 0.2},
    },
    "balanced": {
        "name": "Balanced",
        "description": "Even mix of offensive and defensive tactics",
        "aggression_modifier": 0.0,
        "action_bias": {"attack": 0.5, "defend": 0.4, "super_unit": 0.1},
    },
    "berserker": {
        "name": "Berserker",
        "description": "All-out attack, ignores defensive considerations",
        "aggression_modifier": 0.5,
        "action_bias": {"attack": 0.9, "defend": 0.05, "super_unit": 0.05},
    },
}


def generate_npc_stats(
    archetype_key: str, tech_level_key: str, base_power: int = 50
) -> Dict[str, int]:
    """Generate NPC stats based on archetype and tech level.

    Args:
        archetype_key: One of the ARCHETYPES keys
        tech_level_key: One of the TECH_LEVELS keys
        base_power: Base stat pool to distribute (default 50)

    Returns:
        Dictionary with exosphere, naval, military stats
    """
    archetype = ARCHETYPES.get(archetype_key, ARCHETYPES["nato"])
    tech_level = TECH_LEVELS.get(tech_level_key, TECH_LEVELS["modern"])

    weights = archetype["stat_weights"]
    multiplier = tech_level["stat_multiplier"]

    # Distribute base power according to archetype weights
    stats = {
        "exosphere": int(base_power * weights["exosphere"] * multiplier),
        "naval": int(base_power * weights["naval"] * multiplier),
        "military": int(base_power * weights["military"] * multiplier),
    }

    return stats


def choose_npc_actions(
    war: Dict[str, Any],
    npc_side: str,
    archetype_key: str,
    personality_key: str,
    learning_data: Dict[str, Any],
) -> Tuple[str, str]:
    """AI decision-making for NPC actions.

    Args:
        war: War data dictionary
        npc_side: "attacker" or "defender"
        archetype_key: NPC archetype
        personality_key: NPC personality
        learning_data: Historical performance data for adaptive learning

    Returns:
        Tuple of (main_action, minor_action)
    """
    archetype = ARCHETYPES.get(archetype_key, ARCHETYPES["nato"])
    personality = PERSONALITIES.get(personality_key, PERSONALITIES["balanced"])

    # Calculate effective aggression
    base_aggression = archetype["aggression"]
    personality_mod = personality["aggression_modifier"]
    effective_aggression = base_aggression + personality_mod

    # Adaptive personality adjusts based on tactical momentum
    if personality_key == "adaptive":
        tactical_momentum = war.get("tactical_momentum", 0)
        # If we're winning (momentum in our favor), be more aggressive
        if (npc_side == "attacker" and tactical_momentum > 0) or (
            npc_side == "defender" and tactical_momentum < 0
        ):
            effective_aggression += 0.2
        else:
            effective_aggression -= 0.2

    # Apply learning data (if NPC has been losing, adjust tactics)
    recent_losses = learning_data.get("recent_losses", 0)
    recent_wins = learning_data.get("recent_wins", 0)
    if recent_losses > recent_wins:
        # Become more defensive after losses
        effective_aggression -= 0.2
    elif recent_wins > recent_losses:
        # Become more aggressive after wins
        effective_aggression += 0.1

    # Clamp aggression to 0-1 range
    effective_aggression = max(0.0, min(1.0, effective_aggression))

    # Choose main action
    main_action = _choose_main_action(
        war, npc_side, effective_aggression, personality["action_bias"], archetype
    )

    # Choose minor action
    minor_action = _choose_minor_action(
        war, npc_side, main_action, effective_aggression, archetype
    )

    return main_action, minor_action


def _choose_main_action(
    war: Dict[str, Any],
    npc_side: str,
    aggression: float,
    action_bias: Dict[str, float],
    archetype: Dict[str, Any],
) -> str:
    """Internal: Choose main action for NPC."""
    # Check if super unit is available
    super_unit_available = _has_available_super_unit(war, npc_side)

    # Build weighted action pool
    weights = {}

    # Base weights from personality
    weights["attack"] = action_bias["attack"] * aggression
    weights["defend"] = action_bias["defend"] * (1.0 - aggression)

    # Super unit only if available and archetype prefers it
    if super_unit_available and "super_unit" in archetype["preferred_main_actions"]:
        weights["super_unit"] = action_bias["super_unit"]
    else:
        weights["super_unit"] = 0.0

    # Normalize weights
    total = sum(weights.values())
    if total == 0:
        return "defend"  # Fallback

    normalized = {k: v / total for k, v in weights.items()}

    # Weighted random choice
    return random.choices(
        list(normalized.keys()), weights=list(normalized.values()), k=1
    )[0]


def _choose_minor_action(
    war: Dict[str, Any],
    npc_side: str,
    main_action: str,
    aggression: float,
    archetype: Dict[str, Any],
) -> str:
    """Internal: Choose minor action for NPC."""
    preferred = archetype["preferred_minor_actions"]

    # If we're attacking, bias toward offensive minors
    if main_action == "attack":
        if "prepare_attack" in preferred and random.random() < 0.6:
            return "prepare_attack"
        if "sabotage" in preferred and random.random() < 0.4:
            return "sabotage"

    # If we're defending, bias toward defensive minors
    if main_action == "defend":
        if "fortify_defense" in preferred and random.random() < 0.5:
            return "fortify_defense"
        if "heal" in preferred and random.random() < 0.3:
            return "heal"

    # If we're using super unit, prep for next turn
    if main_action == "super_unit":
        if "prepare_super_unit" in preferred and random.random() < 0.7:
            return "prepare_super_unit"

    # Fallback to random preferred action
    return random.choice(preferred) if preferred else "prepare_attack"


def _has_available_super_unit(war: Dict[str, Any], side: str) -> bool:
    """Check if NPC has a super unit ready to deploy."""
    # Check pending_super_units field (from prepare_super_unit minor action)
    pending = war.get("pending_super_units", {}).get(side, [])
    return len(pending) > 0


def update_learning_data(
    learning_data: Dict[str, Any], outcome: str, margin: int
) -> Dict[str, Any]:
    """Update NPC learning data after a resolution.

    Args:
        learning_data: Current learning data
        outcome: "win", "loss", or "stalemate"
        margin: Victory margin (positive if win, negative if loss)

    Returns:
        Updated learning data
    """
    if "recent_wins" not in learning_data:
        learning_data["recent_wins"] = 0
    if "recent_losses" not in learning_data:
        learning_data["recent_losses"] = 0
    if "history" not in learning_data:
        learning_data["history"] = []

    # Update win/loss counters
    if outcome == "win":
        learning_data["recent_wins"] += 1
    elif outcome == "loss":
        learning_data["recent_losses"] += 1

    # Keep rolling window of last 5 results
    learning_data["history"].append({"outcome": outcome, "margin": margin})
    if len(learning_data["history"]) > 5:
        learning_data["history"] = learning_data["history"][-5:]

    # Decay old results (gradually forget old wins/losses)
    learning_data["recent_wins"] = max(0, learning_data["recent_wins"] - 0.1)
    learning_data["recent_losses"] = max(0, learning_data["recent_losses"] - 0.1)

    return learning_data


def get_npc_config_defaults() -> Dict[str, Any]:
    """Return default NPC configuration for a war."""
    return {
        "enabled": False,
        "side": None,  # "attacker" or "defender"
        "archetype": "nato",
        "tech_level": "modern",
        "personality": "balanced",
        "base_power": 50,
        "learning_data": {},
    }


def apply_npc_config_to_war(
    war: Dict[str, Any], side: str, archetype: str, tech_level: str, personality: str
) -> None:
    """Apply NPC configuration to a war side.

    Args:
        war: War data dictionary
        side: "attacker" or "defender"
        archetype: Archetype key
        tech_level: Tech level key
        personality: Personality key
    """
    # Ensure dual NPC config structure exists
    if "npc_config" not in war:
        war["npc_config"] = {
            "attacker": {
                "enabled": False,
                "archetype": "nato",
                "tech_level": "modern",
                "personality": "balanced",
                "base_power": 50,
                "learning_data": {}
            },
            "defender": {
                "enabled": False,
                "archetype": "nato",
                "tech_level": "modern",
                "personality": "balanced",
                "base_power": 50,
                "learning_data": {}
            }
        }

    # Set NPC config for THIS side
    war["npc_config"][side]["enabled"] = True
    war["npc_config"][side]["archetype"] = archetype
    war["npc_config"][side]["tech_level"] = tech_level
    war["npc_config"][side]["personality"] = personality

    # Generate and apply stats
    stats = generate_npc_stats(archetype, tech_level)
    if "stats" not in war:
        war["stats"] = {"attacker": {}, "defender": {}}

    war["stats"][side] = stats

    # Ensure learning data exists
    if "learning_data" not in war["npc_config"][side]:
        war["npc_config"][side]["learning_data"] = {}
