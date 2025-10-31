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
    # Space-focused archetypes
    "void_fleet": [
        "{npc_name} deep-space carrier battlegroups launch fighter screens, saturating enemy point-defense with coordinated strike craft waves.",
        "Sensors detect {npc_name} capital ships maneuvering into firing positions, their massive weapon arrays charging for broadside volleys.",
        "{npc_name} void fleet executes a carrier strike - swarms of fighters and bombers emerging from hangars to overwhelm enemy formations.",
    ],
    "orbital_supremacy": [
        "{npc_name} orbital platforms align targeting solutions, preparing to rain kinetic death from the high ground of space.",
        "Warning klaxons sound as {npc_name} activates orbital bombardment systems - tungsten rods begin deorbiting toward target coordinates.",
        "{npc_name} space-based weapons come online, orbital lasers and mass drivers achieving firing locks on surface targets.",
    ],
    # Naval-focused archetypes
    "armada": [
        "{npc_name} battlefleet advances in formation - dreadnoughts, carriers, and cruisers presenting a wall of steel and firepower.",
        "Sonar contacts confirm {npc_name} submarine wolfpacks positioning for coordinated torpedo strikes while surface fleet provides distraction.",
        "{npc_name} grand armada launches a naval assault - carrier air wings providing cover as battleships' main guns open fire.",
    ],
    "thalassocracy": [
        "{npc_name} amphibious strike groups surge forward, marines preparing for beach landings while naval artillery softens coastal defenses.",
        "Reports indicate {npc_name} naval empire is executing a sea-control operation, destroyers and frigates establishing maritime dominance.",
        "{npc_name} thalassocratic forces press the attack - combined naval and amphibious assault overwhelming littoral defenses.",
    ],
    "leviathan_corps": [
        "{npc_name} unleashes its bio-engineered titans - massive aquatic beasts rising from the depths to tear into enemy vessels.",
        "Panicked reports describe {npc_name} leviathans breaching alongside the fleet, their tentacles and bio-weapons wreaking havoc.",
        "{npc_name} deep-sea horrors surface en masse, genetically-engineered war-beasts attacking with primal fury.",
    ],
    # Eldritch archetypes
    "void_cult": [
        "{npc_name} reality-warpers channel dark-matter energies, bending space-time to unleash incomprehensible devastation.",
        "Sensors malfunction as {npc_name} cultists invoke their patron entities - physics itself seems to rebel against the enemy.",
        "{npc_name} void-touched forces attack, their weapons channeling energies from dimensions that shouldn't exist.",
    ],
    "eldritch_hive": [
        "{npc_name} biomechanical swarm surges forward - chittering masses of flesh-metal hybrids moving with unnatural coordination.",
        "Contact reports describe {npc_name} hive organisms flowing like liquid death, adapting and evolving mid-combat.",
        "{npc_name} alien swarm-intelligence attacks with incomprehensible tactics - individual units sacrificed without hesitation for hive advantage.",
    ],
    "nightmare_legion": [
        "{npc_name} reality-bending horrors phase into existence, their very presence warping causality and sanity.",
        "Enemy forces report seeing impossible geometries as {npc_name} nightmare entities manifest, attacks coming from angles that don't exist.",
        "{npc_name} aberrant legion strikes from beyond the veil, their weapons operating on principles that defy natural law.",
    ],
    "old_ones": [
        "{npc_name} awakens from eons of slumber, non-Euclidean war-forms emerging to reshape the battlefield into mad geometry.",
        "Witnesses describe {npc_name} cosmic entities attacking with incomprehensible methods - angles that shouldn't exist, colors beyond spectrum.",
        "{npc_name} ancient ones stir, their mere presence causing reality to buckle and sanity to fray at the edges.",
    ],
    "infernal_legions": [
        "{npc_name} daemonic hordes surge forth in hellfire and brimstone - soul-bound war machines screaming across the battlefield.",
        "Sulfurous smoke heralds {npc_name} infernal assault - lesser daemons swarming forward while greater entities command from the rear.",
        "{npc_name} abyssal forces attack with daemonic fury, their pact-weapons and hellfire artillery turning the battlefield into an inferno.",
    ],
    # Psionic archetypes
    "psionic_covenant": [
        "{npc_name} telepaths coordinate perfect tactical synchronization, telekinetic warfare tearing through enemy formations.",
        "Reports indicate {npc_name} mind-blade infantry advancing in psychic harmony, their thoughts moving as one lethal whole.",
        "{npc_name} psionic warriors strike with mental and physical force - telekinetic barriers protecting advancing troops as mind-lances pierce enemy defenses.",
    ],
    "thought_collective": [
        "{npc_name} unified gestalt executes flawless maneuvers, thousands of bodies operating as one distributed consciousness.",
        "Enemy commanders report perfect coordination from {npc_name} forces - every soldier acting in absolute tactical unison.",
        "{npc_name} psychic collective attacks, their hive-mind tactical processing outmaneuvering individual commanders by orders of magnitude.",
    ],
    "psychic_ascendancy": [
        "{npc_name} reality-warpers manipulate probability fields, enemy weapons misfiring while their own shots find impossible angles.",
        "Combat reports describe {npc_name} psions bending causality itself - bullets curving mid-flight, explosions defying physics to reach targets.",
        "{npc_name} ascended minds wage war on reality, precognition and probability manipulation turning every engagement to their advantage.",
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
    # Space-focused archetypes
    "void_fleet": [
        "{npc_name} carrier battlegroups establish defensive formations, fighter screens creating layered point-defense perimeters.",
        "Reports indicate {npc_name} capital ships are taking up defensive positions, overlapping fire arcs creating kill zones.",
        "{npc_name} void fleet transitions to defensive posture - carriers launching CAP while battleships anchor the formation.",
    ],
    "orbital_supremacy": [
        "{npc_name} orbital platforms reposition to defensive sectors, point-defense grids activating to intercept incoming threats.",
        "Warning systems show {npc_name} space-based defenses going active - laser grids and interceptor platforms standing ready.",
        "{npc_name} orbital assets shift to defensive mode, overlapping coverage creating near-impenetrable high-ground defense.",
    ],
    # Naval-focused archetypes
    "armada": [
        "{npc_name} battlefleet forms defensive screen, destroyers establishing ASW perimeter while capital ships provide area denial.",
        "Tactical reports show {npc_name} naval forces establishing layered defense - submarines, surface combatants, and air cover working in concert.",
        "{npc_name} grand armada assumes defensive formation, presenting overlapping fields of fire and mutual support.",
    ],
    "thalassocracy": [
        "{npc_name} naval empire establishes sea control, coastal defenses and naval artillery creating layered defensive zones.",
        "Reports indicate {npc_name} forces fortifying maritime approaches, mines and patrol craft establishing denied areas.",
        "{npc_name} thalassocratic defenses activate - coastal batteries, naval patrols, and amphibious reserves ready to repel invasion.",
    ],
    "leviathan_corps": [
        "{npc_name} bio-engineered sentinels take up defensive positions, massive creatures forming living barriers beneath the waves.",
        "Sonar contacts confirm {npc_name} leviathans patrolling defensive perimeter, their massive bulk deterring approach.",
        "{npc_name} aquatic titans settle into defensive stance, bio-weapons and armored hides creating formidable obstacles.",
    ],
    # Eldritch archetypes
    "void_cult": [
        "{npc_name} reality-warpers establish eldritch wards, bending space itself to create impossible defensive geometries.",
        "Sensors detect {npc_name} void-touched defenses manifesting - dimensional barriers that defy conventional targeting.",
        "{npc_name} cultists invoke defensive pacts, dark-matter entities forming shields against approaching threats.",
    ],
    "eldritch_hive": [
        "{npc_name} biomechanical swarm spreads into defensive formation, individual organisms sacrificing themselves to form living walls.",
        "Reports describe {npc_name} hive creating adaptive defensive structures - flesh-metal fortifications growing and evolving in real-time.",
        "{npc_name} alien swarm-intelligence establishes defensive perimeter, hive organisms burrowing and fortifying with terrifying efficiency.",
    ],
    "nightmare_legion": [
        "{npc_name} reality-bending horrors phase into defensive positions, occupying spaces that technically don't exist.",
        "Enemy forces report impossible defenses from {npc_name} - barriers that exist in dimensions orthogonal to normal space.",
        "{npc_name} aberrant entities establish nightmare fortifications, their mere presence warping approach vectors into labyrinthine death-traps.",
    ],
    "old_ones": [
        "{npc_name} ancient entities settle into defensive slumber, their dreaming presence creating madness-inducing defensive barriers.",
        "Witnesses describe {npc_name} cosmic horrors establishing non-Euclidean fortifications - angles that shouldn't exist forming impenetrable walls.",
        "{npc_name} old ones manifest passive defenses, reality itself buckling to protect their positions from mortal comprehension.",
    ],
    "infernal_legions": [
        "{npc_name} daemonic forces establish hellish fortifications, summoning circles and soul-fire barriers repelling attackers.",
        "Sulfurous smoke marks {npc_name} infernal defenses - lesser daemons manning ramparts while greater entities anchor the line.",
        "{npc_name} abyssal legions dig in, pact-bound war machines creating overlapping fields of hellfire and damnation.",
    ],
    # Psionic archetypes
    "psionic_covenant": [
        "{npc_name} telepaths establish unified defensive mindscape, telekinetic barriers forming invisible walls against incoming fire.",
        "Reports indicate {npc_name} mind-blade warriors taking defensive positions, psychic wards protecting key sectors.",
        "{npc_name} psionic defenders create mental-physical barriers, thoughts made solid to deflect enemy assaults.",
    ],
    "thought_collective": [
        "{npc_name} unified gestalt shifts to defensive configuration, distributed consciousness optimizing every defensive position simultaneously.",
        "Enemy commanders report perfect defensive coordination from {npc_name} - every unit positioned for maximum mutual support.",
        "{npc_name} psychic collective assumes defensive posture, hive-mind tactical processing creating flawless defensive network.",
    ],
    "psychic_ascendancy": [
        "{npc_name} reality-warpers bend probability to defensive advantage, enemy attacks mysteriously veering away from critical positions.",
        "Combat reports describe {npc_name} psions manipulating causality defensively - incoming fire losing momentum, explosives failing at critical moments.",
        "{npc_name} ascended minds wage defensive probability warfare, precognition allowing perfect positioning against every attack vector.",
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
    # Space-focused archetypes
    "void_fleet": [
        "{npc_name} commits its flag-carrier {super_unit_name} to battle, the massive void-titan launching its full strike complement.",
        "Sensors detect {npc_name} deploying {super_unit_name}, a super-capital that dwarfs entire battlefleets.",
    ],
    "orbital_supremacy": [
        "{npc_name} activates {super_unit_name}, orbital weapons platform - targeting solutions locked, firing sequence initiated.",
        "Warning klaxons blare as {npc_name} brings {super_unit_name} online, space-based doomsday weapon achieving firing position.",
    ],
    # Naval-focused archetypes
    "armada": [
        "{npc_name} deploys its pride and terror {super_unit_name}, a super-dreadnought that outguns entire fleets.",
        "Battle-stations sound as {npc_name} commits {super_unit_name} to the engagement, the ultimate naval weapons platform.",
    ],
    "thalassocracy": [
        "{npc_name} unleashes {super_unit_name}, the jewel of their maritime empire - carrier-battleship hybrid of terrifying capability.",
        "Reports confirm {npc_name} has deployed {super_unit_name}, amphibious assault titan that combines naval firepower with marine shock troops.",
    ],
    "leviathan_corps": [
        "{npc_name} awakens {super_unit_name}, their apex bio-titan - a leviathan whose roar sends entire fleets fleeing.",
        "Sonar goes haywire as {npc_name} summons {super_unit_name}, a bio-engineered horror of unprecedented scale and ferocity.",
    ],
    # Eldritch archetypes
    "void_cult": [
        "{npc_name} completes the summoning of {super_unit_name}, reality tears open to admit their patron entity.",
        "Cultists chant as {npc_name} manifests {super_unit_name}, a dark-matter abomination from beyond comprehension.",
    ],
    "eldritch_hive": [
        "{npc_name} births {super_unit_name}, a hive-titan whose biomechanical horror eclipses all previous swarm-forms.",
        "Sensors detect massive bio-signatures as {npc_name} deploys {super_unit_name}, the ultimate evolution of their swarm intelligence.",
    ],
    "nightmare_legion": [
        "{npc_name} tears reality asunder to unleash {super_unit_name}, an aberration that exists in too many dimensions simultaneously.",
        "Witnesses go mad as {npc_name} manifests {super_unit_name}, a nightmare given form that defies natural law.",
    ],
    "old_ones": [
        "{npc_name} awakens fully, {super_unit_name} rising from eons of dreaming - non-Euclidean war-form reshaping reality itself.",
        "The stars align wrong as {npc_name} calls forth {super_unit_name}, cosmic horror whose mere existence breaks mortal minds.",
    ],
    "infernal_legions": [
        "{npc_name} completes the ritual, summoning {super_unit_name} from the Abyss - greater daemon-prince of war incarnate.",
        "Hellfire erupts as {npc_name} unleashes {super_unit_name}, daemonic war-engine bound by soul-pacts and blood sacrifices.",
    ],
    # Psionic archetypes
    "psionic_covenant": [
        "{npc_name} manifests {super_unit_name}, their greatest psychic warrior - a telepath whose mind touches thousands simultaneously.",
        "Psychic pressure builds as {npc_name} deploys {super_unit_name}, psionic nexus amplifying the covenant's mental might.",
    ],
    "thought_collective": [
        "{npc_name} activates {super_unit_name}, gestalt-core that unifies the collective into one transcendent consciousness.",
        "The hive-mind pulses as {npc_name} brings {super_unit_name} online, distributed intelligence achieving unprecedented coordination.",
    ],
    "psychic_ascendancy": [
        "{npc_name} unleashes {super_unit_name}, reality-warper whose precognition and probability manipulation approach divine omniscience.",
        "Causality buckles as {npc_name} deploys {super_unit_name}, ascended psion who rewrites the battlefield's very fate.",
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
