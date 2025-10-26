"""Narrative template generation for NPC actions in PvE wars."""

from __future__ import annotations

import random
from typing import Any, Dict

# ========== NARRATIVE TEMPLATES ==========
# Templates use {placeholders} that get filled in with context

ATTACK_NARRATIVES = {
    "nato": [
        "{npc_name} launches a coordinated combined-arms offensive, with air support softening enemy positions before mechanized units advance under artillery cover.",
        "Intelligence reports indicate {npc_name} is executing a textbook combined-arms assault with air superiority and precision strikes on key targets.",
        "{npc_name} commits its professional forces to a systematic advance, utilizing superior coordination and firepower to overwhelm defensive positions.",
    ],
    "csat": [
        "{npc_name} masses its ground forces for a large-scale assault, waves of infantry and armor rolling forward in overwhelming numbers.",
        "Reports indicate {npc_name} is mobilizing massive reserves, preparing to drown the enemy in steel and bodies.",
        "{npc_name} launches a broad-front offensive with overwhelming numerical superiority, accepting casualties to achieve breakthrough.",
    ],
    "guerrilla": [
        "{npc_name} strikes unexpectedly at a vulnerable position, hitting hard before melting back into the terrain.",
        "Intelligence reports {npc_name} guerrilla units conducting hit-and-run raids on supply lines and isolated positions.",
        "{npc_name} emerges from concealment to ambush enemy forces, inflicting casualties before disappearing.",
    ],
    "swarm": [
        "{npc_name} unleashes swarms of drones and autonomous units, saturating enemy defenses with sheer numbers.",
        "Radar contacts indicate {npc_name} is deploying massive drone swarms, overwhelming point defense systems.",
        "{npc_name} floods the battlefield with cheap, expendable units - quantity has a quality all its own.",
    ],
    "elite": [
        "{npc_name} deploys its elite special forces units for a surgical strike on high-value targets.",
        "Intelligence reports {npc_name} special operations teams conducting precision raids deep behind enemy lines.",
        "{npc_name} commits its best units to a carefully planned assault, every move calculated for maximum effect.",
    ],
    "defensive_bloc": [
        "{npc_name} launches a cautious counter-offensive from its fortified positions, careful not to overextend.",
        "Reports indicate {npc_name} is conducting limited counter-attacks to reclaim lost ground while maintaining defensive depth.",
        "{npc_name} sortie from their defensive lines in strength, striking at weakened enemy positions before falling back.",
    ],
    "insurgent": [
        "{npc_name} rebel forces strike without warning - car bombs, IEDs, and ambushes targeting enemy patrols and checkpoints.",
        "Intelligence reports {npc_name} insurgents conducting coordinated terrorist attacks across multiple locations simultaneously.",
        "{npc_name} cells emerge from hiding to launch deadly ambushes, then vanish into the civilian population before reinforcements arrive.",
    ],
}

DEFEND_NARRATIVES = {
    "nato": [
        "{npc_name} establishes layered defensive positions with overlapping fields of fire and air cover on standby.",
        "Reports indicate {npc_name} is digging in with professional discipline, preparing defensive networks and fire support plans.",
        "{npc_name} shifts to defensive posture, establishing kill zones and coordinate fire plans.",
    ],
    "csat": [
        "{npc_name} masses its forces in deep defensive positions, prepared to trade space for time and attacker casualties.",
        "Intelligence reports {npc_name} constructing extensive defensive works and concentrating reserves for counter-attacks.",
        "{npc_name} establishes defense in depth, multiple fallback lines ensuring no easy breakthrough.",
    ],
    "guerrilla": [
        "{npc_name} melts into the terrain, setting booby traps and preparing ambush positions along likely approach routes.",
        "Reports indicate {npc_name} guerrillas have gone to ground, turning the entire theater into a deadly maze of IEDs and sniper positions.",
        "{npc_name} disappears into the countryside, making every meter of advance cost the enemy blood.",
    ],
    "swarm": [
        "{npc_name} deploys autonomous defensive drones and sensor nets, creating a networked defense perimeter.",
        "Intelligence reports {npc_name} establishing AI-controlled defensive screens with thousands of cheap sensor/weapons platforms.",
        "{npc_name} saturates the defensive zone with autonomous units, creating multiple redundant defensive layers.",
    ],
    "elite": [
        "{npc_name} elite units establish precision defensive positions at key chokepoints, maximizing their qualitative advantage.",
        "Reports indicate {npc_name} special forces have fortified critical terrain with expert fields of fire and prepared fall-back positions.",
        "{npc_name} deploys its best troops to anchor the defensive line, holding critical positions against all odds.",
    ],
    "defensive_bloc": [
        "{npc_name} reinforces its already formidable fortifications, turning positions into near-impregnable strong points.",
        "Intelligence reports {npc_name} conducting extensive fortification efforts, concrete bunkers and prepared artillery zones.",
        "{npc_name} settles into its preferred defensive posture, prepared to bleed any attacker white.",
    ],
    "insurgent": [
        "{npc_name} rebels go to ground, hiding among civilians and preparing IED ambushes for enemy patrols.",
        "Intelligence reports {npc_name} insurgents have dispersed into cells, making every street and building a potential threat.",
        "{npc_name} forces fade into the population, making conventional military operations nearly impossible without massive collateral damage.",
    ],
}

SUPER_UNIT_NARRATIVES = {
    "nato": [
        "{npc_name} commits its advanced {super_unit_name} to the battle, bringing cutting-edge technology to bear.",
        "Reconnaissance confirms {npc_name} has deployed {super_unit_name}, a game-changing asset on the battlefield.",
    ],
    "csat": [
        "{npc_name} unleashes {super_unit_name}, a massive weapons platform designed to dominate the battlefield.",
        "Reports confirm {npc_name} has committed {super_unit_name} to combat, a behemoth of firepower and armor.",
    ],
    "guerrilla": [
        "{npc_name} reveals {super_unit_name}, a weapon that levels the playing field despite their limited resources.",
        "Intelligence indicates {npc_name} has somehow acquired {super_unit_name}, a devastating capability in their hands.",
    ],
    "swarm": [
        "{npc_name} activates {super_unit_name}, a swarm-mind controller coordinating thousands of autonomous units.",
        "Reports show {npc_name} deploying {super_unit_name}, an AI hive-mind that makes their drone swarms truly terrifying.",
    ],
    "elite": [
        "{npc_name} deploys {super_unit_name}, the pinnacle of their special operations capabilities.",
        "Intelligence confirms {npc_name} has committed {super_unit_name}, their ultimate ace in the hole.",
    ],
    "defensive_bloc": [
        "{npc_name} activates {super_unit_name}, a fortress weapons platform designed to anchor their defensive line.",
        "Reports indicate {npc_name} has brought {super_unit_name} online, turning their position into a death trap.",
    ],
    "insurgent": [
        "{npc_name} reveals {super_unit_name}, a terror weapon designed to strike fear and create chaos.",
        "Intelligence reports {npc_name} has deployed {super_unit_name}, a weapon of terror acquired through unknown means.",
    ],
}

MINOR_ACTION_NARRATIVES = {
    "prepare_attack": [
        "{npc_name} conducts reconnaissance and coordinates fire support for the next offensive.",
        "Reports indicate {npc_name} is positioning assets and gathering intelligence for an upcoming strike.",
        "{npc_name} prepares the battlefield, softening targets and coordinating approach routes.",
    ],
    "sabotage": [
        "{npc_name} conducts covert operations behind enemy lines, sabotaging supply depots and communication infrastructure.",
        "Intelligence reports {npc_name} saboteurs have struck enemy logistics, causing disruption and confusion.",
        "{npc_name} special operations teams successfully sabotage key enemy assets.",
    ],
    "fortify_defense": [
        "{npc_name} reinforces defensive positions with additional obstacles, mines, and prepared positions.",
        "Reports indicate {npc_name} is digging in deeper, establishing stronger defensive works.",
        "{npc_name} strengthens its defensive perimeter with engineering and fortification efforts.",
    ],
    "heal": [
        "{npc_name} rotates exhausted units out of the line, bringing in fresh reserves and conducting maintenance.",
        "Intelligence reports {npc_name} is consolidating forces and repairing damaged equipment.",
        "{npc_name} takes time to regroup, rest, and recover from recent combat operations.",
    ],
    "prepare_super_unit": [
        "{npc_name} moves {super_unit_name} into position, preparing it for combat deployment.",
        "Reports confirm {npc_name} is preparing {super_unit_name} for battlefield commitment.",
        "{npc_name} conducts final checks on {super_unit_name}, readying it for action.",
    ],
}

TECH_LEVEL_FLAVOR = {
    "legacy": [
        "using Cold War-era equipment",
        "relying on proven but outdated technology",
        "with vintage but reliable hardware",
    ],
    "modern": [
        "with contemporary military technology",
        "using current-generation equipment",
        "deploying modern, well-maintained forces",
    ],
    "advanced": [
        "with cutting-edge near-future tech",
        "deploying advanced weapons systems",
        "using sophisticated next-gen equipment",
    ],
    "cutting_edge": [
        "with bleeding-edge 2240 technology",
        "deploying experimental weapons platforms",
        "using technology that seems almost magical",
    ],
}

PERSONALITY_FLAVOR = {
    "aggressive": [
        "The attack is relentless and brutal.",
        "No hesitation, no mercy.",
        "They're going all-in.",
    ],
    "defensive": [
        "The approach is cautious and measured.",
        "They're not taking unnecessary risks.",
        "Every move calculated to minimize exposure.",
    ],
    "adaptive": [
        "They've adjusted their tactics based on recent battles.",
        "The approach shows learned lessons from previous engagements.",
        "They're evolving their strategy in real-time.",
    ],
    "balanced": [
        "The approach is well-rounded and professional.",
        "They maintain tactical flexibility.",
        "A methodical, by-the-book operation.",
    ],
    "berserker": [
        "The attack is absolutely savage and reckless.",
        "They're throwing everything at you with no regard for their own losses.",
        "Pure, unrestrained aggression.",
    ],
}


def generate_npc_narrative(
    war: Dict[str, Any],
    npc_side: str,
    main_action: str,
    minor_action: str,
    archetype: str,
    tech_level: str,
    personality: str,
) -> str:
    """Generate narrative flavor text for NPC action.

    Args:
        war: War data dictionary
        npc_side: "attacker" or "defender"
        main_action: Main action chosen
        minor_action: Minor action chosen
        archetype: NPC archetype
        tech_level: NPC tech level
        personality: NPC personality

    Returns:
        Formatted narrative string (150+ characters to meet player-driven requirements)
    """
    npc_name = war.get(npc_side, "NPC Forces")

    # Get main action narrative
    if main_action == "attack":
        main_template = random.choice(ATTACK_NARRATIVES.get(archetype, ATTACK_NARRATIVES["nato"]))
    elif main_action == "defend":
        main_template = random.choice(DEFEND_NARRATIVES.get(archetype, DEFEND_NARRATIVES["nato"]))
    elif main_action == "super_unit":
        main_template = random.choice(SUPER_UNIT_NARRATIVES.get(archetype, SUPER_UNIT_NARRATIVES["nato"]))
        # Get super unit name if available
        super_unit_name = "advanced weapons platform"  # Fallback
        pending = war.get("pending_super_units", {}).get(npc_side, [])
        if pending:
            super_unit_name = pending[0].get("name", super_unit_name)
        main_template = main_template.replace("{super_unit_name}", super_unit_name)
    else:
        main_template = "{npc_name} takes action."

    main_narrative = main_template.replace("{npc_name}", npc_name)

    # Get minor action narrative
    minor_template = random.choice(MINOR_ACTION_NARRATIVES.get(minor_action, ["{npc_name} conducts supporting operations."]))
    if "{super_unit_name}" in minor_template:
        super_unit_name = "advanced weapons platform"
        pending = war.get("pending_super_units", {}).get(npc_side, [])
        if pending:
            super_unit_name = pending[0].get("name", super_unit_name)
        minor_template = minor_template.replace("{super_unit_name}", super_unit_name)
    minor_narrative = minor_template.replace("{npc_name}", npc_name)

    # Get flavor additions
    tech_flavor = random.choice(TECH_LEVEL_FLAVOR.get(tech_level, TECH_LEVEL_FLAVOR["modern"]))
    personality_flavor = random.choice(PERSONALITY_FLAVOR.get(personality, PERSONALITY_FLAVOR["balanced"]))

    # Combine into full narrative
    narrative = f"{main_narrative} {minor_narrative} They're operating {tech_flavor}. {personality_flavor}"

    return narrative
