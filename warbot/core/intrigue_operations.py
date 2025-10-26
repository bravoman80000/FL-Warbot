"""Operation mechanics and resolution for the intrigue system."""

from __future__ import annotations

import random
from typing import Any, Dict, List, Tuple

# ========== OPERATION TYPES ==========
OPERATION_TYPES = {
    "espionage": {
        "name": "Espionage",
        "description": "Gather intelligence on target faction (stats, wars, ongoing operations)",
        "base_dc": 12,
        "base_detection": 0.15,
        "cooldown_hours": 12,
        "emoji": "🕵️",
    },
    "sabotage": {
        "name": "Sabotage",
        "description": "Damage infrastructure and reduce faction stats in ongoing wars",
        "base_dc": 14,
        "base_detection": 0.30,
        "cooldown_hours": 24,
        "emoji": "💣",
    },
    "rebellion": {
        "name": "Incite Rebellion",
        "description": "Foment internal uprising in target territory",
        "base_dc": 16,
        "base_detection": 0.50,
        "cooldown_hours": 72,
        "emoji": "⚔️",
    },
    "influence": {
        "name": "Spread Influence",
        "description": "Expand political, religious, or ideological control",
        "base_dc": 13,
        "base_detection": 0.20,
        "cooldown_hours": 24,
        "emoji": "📜",
    },
    "assassination": {
        "name": "Assassination",
        "description": "Eliminate a key figure or leader",
        "base_dc": 18,
        "base_detection": 0.40,
        "cooldown_hours": 168,  # 1 week
        "emoji": "🗡️",
    },
    "counterintel": {
        "name": "Counter-Intelligence",
        "description": "Detect and disrupt enemy intrigue operations",
        "base_dc": 10,
        "base_detection": 0.10,
        "cooldown_hours": 12,
        "emoji": "🛡️",
    },
}


def calculate_operation_modifiers(operation: Dict[str, Any]) -> Tuple[List[Tuple[str, int]], int]:
    """Calculate all modifiers for an intrigue operation.

    Returns:
        Tuple of (modifier_list, total_modifier)
    """
    modifiers: List[Tuple[str, int]] = []
    total = 0

    op_type = operation.get("type")
    scale = operation.get("scale", "medium")
    operator_skill = operation.get("operator_skill", 0)
    target_strength = operation.get("target_strength", "medium")

    # 1. Operator skill modifier
    if operator_skill != 0:
        modifiers.append(("Operator Skill", operator_skill))
        total += operator_skill

    # 2. Scale modifier (larger = harder but more impactful)
    scale_mods = {
        "small": 2,      # Easier to hide, less impact
        "medium": 0,     # Baseline
        "large": -2,     # Harder to execute
        "massive": -4,   # Very difficult
    }
    scale_mod = scale_mods.get(scale, 0)
    if scale_mod != 0:
        modifiers.append(("Operation Scale", scale_mod))
        total += scale_mod

    # 3. Target strength modifier
    strength_mods = {
        "weak": 3,
        "medium": 0,
        "strong": -2,
        "very_strong": -4,
    }
    strength_mod = strength_mods.get(target_strength, 0)
    if strength_mod != 0:
        modifiers.append(("Target Strength", strength_mod))
        total += strength_mod

    # 4. Operation-specific modifiers
    if op_type == "rebellion":
        # Rebellion easier if target has unrest
        unrest_level = operation.get("target_unrest", "low")
        unrest_mods = {"low": -2, "medium": 0, "high": 2, "critical": 4}
        unrest_mod = unrest_mods.get(unrest_level, 0)
        if unrest_mod != 0:
            modifiers.append(("Target Unrest", unrest_mod))
            total += unrest_mod

    elif op_type == "influence":
        # Influence easier if cultural similarity
        similarity = operation.get("cultural_similarity", "neutral")
        similarity_mods = {"opposed": -3, "neutral": 0, "similar": 2, "identical": 4}
        similarity_mod = similarity_mods.get(similarity, 0)
        if similarity_mod != 0:
            modifiers.append(("Cultural Similarity", similarity_mod))
            total += similarity_mod

    elif op_type == "assassination":
        # Assassination affected by target security
        security = operation.get("target_security", "medium")
        security_mods = {"low": 3, "medium": 0, "high": -3, "maximum": -5}
        security_mod = security_mods.get(security, 0)
        if security_mod != 0:
            modifiers.append(("Target Security", security_mod))
            total += security_mod

    elif op_type == "counterintel":
        # Counter-intel boosted by defensive posture
        defensive = operation.get("defensive_stance", False)
        if defensive:
            modifiers.append(("Defensive Stance", 2))
            total += 2

    # 5. Active counter-intelligence protection (from target faction)
    if operation.get("target_has_counterintel", False):
        modifiers.append(("Enemy Counter-Intel", -3))
        total -= 3

    return modifiers, total


def resolve_operation(
    operation: Dict[str, Any], roll: int
) -> Tuple[str, List[str]]:
    """Resolve an intrigue operation.

    Args:
        operation: Operation dictionary
        roll: D20 roll result

    Returns:
        Tuple of (status, effects_list)
        status: "success", "partial", "failure", "detected"
        effects_list: List of narrative effect strings
    """
    modifiers, total_mod = calculate_operation_modifiers(operation)
    total_result = roll + total_mod
    difficulty = operation.get("difficulty")

    # Store results in operation
    operation["roll"] = roll
    operation["modifiers"] = modifiers
    operation["total"] = total_result

    effects = []

    # Check for critical success/failure
    if roll == 20:
        status = "success"
        effects.append("🎯 **Critical Success!** Operation executed flawlessly.")
        # Bonus: No detection roll needed
        operation["detection_risk"] = 0.0
        return status, effects

    elif roll == 1:
        status = "detected"
        effects.append("💥 **Critical Failure!** Operation compromised and agents identified.")
        operation["detected_by"] = operation.get("target_faction")
        return status, effects

    # Regular resolution
    margin = total_result - difficulty

    if margin >= 10:
        # Exceptional success
        status = "success"
        effects.append("✨ **Exceptional Success!** Operation exceeded all expectations.")
        # Reduce detection risk
        operation["detection_risk"] *= 0.5

    elif margin >= 5:
        # Success
        status = "success"
        effects.append("✅ **Success!** Operation completed successfully.")

    elif margin >= 0:
        # Marginal success / Partial success
        status = "partial"
        effects.append("⚠️ **Partial Success!** Operation had mixed results.")
        # Increase detection risk
        operation["detection_risk"] *= 1.5

    elif margin >= -5:
        # Failure
        status = "failure"
        effects.append("❌ **Failure!** Operation did not achieve objectives.")
        # Significant detection risk increase
        operation["detection_risk"] *= 2.0

    else:
        # Major failure
        status = "failure"
        effects.append("💀 **Major Failure!** Operation backfired spectacularly.")
        # Automatic detection
        operation["detection_risk"] = 1.0

    # Clamp detection risk
    operation["detection_risk"] = min(1.0, operation["detection_risk"])

    return status, effects


def roll_detection(operation: Dict[str, Any]) -> Tuple[bool, str]:
    """Roll for detection of an intrigue operation.

    Args:
        operation: Operation dictionary with detection_risk field

    Returns:
        Tuple of (detected, description)
    """
    detection_risk = operation.get("detection_risk", 0.25)

    # Roll percentage
    roll = random.random()

    if roll < detection_risk:
        # Detected!
        operation["detected_by"] = operation.get("target_faction")
        operation["detection_rolled"] = True

        # Describe how they were caught
        risk_level = detection_risk * 100
        if risk_level >= 70:
            description = "🚨 **DETECTED!** Operation was obvious and immediately noticed."
        elif risk_level >= 40:
            description = "🚨 **DETECTED!** Counter-intelligence identified the operation."
        else:
            description = "🚨 **DETECTED!** A stroke of bad luck exposed the operation."

        return True, description

    else:
        # Not detected
        operation["detection_rolled"] = True
        description = "✅ **Undetected.** Operation remains covert."
        return False, description


def get_operation_impact_description(operation: Dict[str, Any], status: str) -> List[str]:
    """Generate narrative description of operation impacts.

    Args:
        operation: Completed operation
        status: "success", "partial", "failure", "detected"

    Returns:
        List of impact description strings
    """
    impacts = []
    op_type = operation.get("type")
    scale = operation.get("scale", "medium")

    if status == "failure" or status == "detected":
        impacts.append("No strategic impact due to operation failure.")
        return impacts

    # Success or partial success
    if op_type == "espionage":
        if status == "success":
            impacts.append("📊 Complete intelligence dossier obtained:")
            impacts.append("  - Full faction stats revealed")
            impacts.append("  - Active wars and status disclosed")
            impacts.append("  - Ongoing intrigue operations exposed")
        else:  # partial
            impacts.append("📊 Partial intelligence gathered:")
            impacts.append("  - Some faction information obtained")
            impacts.append("  - War status partially revealed")

    elif op_type == "sabotage":
        target_category = operation.get("target_category", "military")
        reduction_map = {"small": 5, "medium": 10, "large": 15, "massive": 20}
        reduction = reduction_map.get(scale, 10)

        if status == "partial":
            reduction = reduction // 2

        impacts.append(f"💣 Infrastructure damage inflicted:")
        impacts.append(f"  - {target_category.title()} capacity reduced by {reduction}")
        impacts.append(f"  - Effect applies to all active wars")

    elif op_type == "rebellion":
        if status == "success":
            impacts.append("⚔️ Major uprising triggered:")
            impacts.append("  - Territory destabilized")
            impacts.append("  - GM may create NPC rebellion war")
            impacts.append("  - Target faction suffers -2 to all actions until resolved")
        else:  # partial
            impacts.append("⚔️ Minor unrest sparked:")
            impacts.append("  - Territory partially destabilized")
            impacts.append("  - Target faction suffers -1 to all actions for 1 turn")

    elif op_type == "influence":
        influence_type = operation.get("influence_type", "political")
        if status == "success":
            impacts.append(f"📜 {influence_type.title()} influence firmly established:")
            impacts.append(f"  - {scale.title()} scale cultural shift")
            impacts.append(f"  - Long-term loyalty to operator faction")
        else:  # partial
            impacts.append(f"📜 {influence_type.title()} influence partially spread:")
            impacts.append(f"  - Minor cultural penetration")
            impacts.append(f"  - Temporary alignment shift")

    elif op_type == "assassination":
        target_name = operation.get("target_name", "key figure")
        if status == "success":
            impacts.append(f"🗡️ {target_name} eliminated:")
            impacts.append(f"  - Leadership vacuum created")
            impacts.append(f"  - Target faction weakened significantly")
            impacts.append(f"  - May trigger succession crisis")
        else:  # partial
            impacts.append(f"🗡️ {target_name} injured but survived:")
            impacts.append(f"  - Temporary incapacitation")
            impacts.append(f"  - Target faction disrupted")

    elif op_type == "counterintel":
        if status == "success":
            impacts.append("🛡️ Counter-intelligence network established:")
            impacts.append("  - Active protection against enemy operations")
            impacts.append("  - +3 modifier to detect incoming intrigue")
            impacts.append("  - Enemy operations have -3 penalty")
        else:  # partial
            impacts.append("🛡️ Basic counter-intelligence in place:")
            impacts.append("  - Limited protection established")
            impacts.append("  - +1 modifier to detect incoming intrigue")

    return impacts


def get_detection_consequences(operation: Dict[str, Any]) -> List[str]:
    """Describe the consequences of being detected.

    Args:
        operation: Detected operation

    Returns:
        List of consequence strings
    """
    consequences = []
    op_type = operation.get("type")

    consequences.append("🚨 **Operation Exposed!** Consequences:")
    consequences.append(f"  - {operation.get('operator_faction')} identified as aggressor")
    consequences.append(f"  - {operation.get('target_faction')} gains casus belli for war")
    consequences.append(f"  - Diplomatic relations severely damaged")

    # Operation-specific consequences
    if op_type in ("sabotage", "assassination", "rebellion"):
        consequences.append("  - May trigger immediate war declaration")
        consequences.append("  - Target faction gains +2 to all actions vs operator for 3 turns")

    elif op_type == "espionage":
        consequences.append("  - Agents captured and interrogated")
        consequences.append("  - Counter-intelligence operations likely")

    elif op_type == "influence":
        consequences.append("  - Propaganda campaign backfires")
        consequences.append("  - Target population turns against operator faction")

    return consequences
