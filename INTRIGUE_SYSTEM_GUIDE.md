# Intrigue System Guide

Complete guide to covert operations: espionage, sabotage, rebellion, assassination, influence campaigns, and counter-intelligence.

## Overview

The Intrigue system allows players to conduct covert operations beyond direct warfare. Operations are roll-based with detection risks - success grants strategic advantages, but getting caught has serious consequences.

**Key Features:**
- 6 operation types with unique mechanics
- Roll-based resolution (d20 + modifiers vs DC)
- Detection risk system (get caught = diplomatic incident)
- Cooldowns per operation type
- Integration with war system (sabotage affects stats, rebellion triggers wars)
- Intelligence gathering (espionage reveals enemy capabilities)

## Operation Types

### 🕵️ Espionage
**Purpose:** Gather intelligence on target faction
**Base DC:** 12
**Detection Risk:** 15%
**Cooldown:** 12 hours

**Success reveals:**
- Faction military stats (exosphere/naval/military)
- Active wars and war status
- Ongoing intrigue operations

**Use when:** You need tactical information before declaring war or want to track enemy capabilities.

---

### 💣 Sabotage
**Purpose:** Damage infrastructure and reduce faction stats
**Base DC:** 14
**Detection Risk:** 30%
**Cooldown:** 24 hours

**Target categories:**
- **Military** (ground forces)
- **Naval** (sea/water forces)
- **Exosphere** (space/air forces)

**Stat reduction by scale:**
- Small: -5
- Medium: -10
- Large: -15
- Massive: -20

**Effect:** Applies to ALL active wars involving target faction.

**Use when:** Enemy is stronger than you in a specific domain (reduce their naval to level the playing field).

---

### ⚔️ Incite Rebellion
**Purpose:** Foment internal uprising in target territory
**Base DC:** 16
**Detection Risk:** 50%
**Cooldown:** 72 hours (3 days)

**Modifiers:**
- Target unrest level (low/medium/high/critical): -2 to +4

**Success effects:**
- Territory destabilized
- GM may create NPC rebellion war using Insurgent archetype
- Target faction suffers -2 to all actions until rebellion resolved

**Partial success:**
- Minor unrest
- Target faction -1 to all actions for 1 turn

**IMPORTANT: Gradual Escalation**
- Rebellions typically require **2-3 successful operations** to trigger a full war
- First success: Unrest begins, faction takes penalties
- Second success: Uprising intensifies, major instability
- Third success: Full rebellion, GM creates NPC war (Insurgent vs Empire)
- Use `/war set_npc` to configure both sides as NPCs for autonomous conflict
- One-shot rebellions are rare and require exceptional circumstances (critical unrest + nat 20)

**Use when:** Target has internal problems (high unrest) or you want to tie them down fighting on two fronts.

---

### 📜 Spread Influence
**Purpose:** Expand political, religious, or ideological control
**Base DC:** 13
**Detection Risk:** 20%
**Cooldown:** 24 hours

**Influence types:**
- Political
- Religious
- Ideological
- Cultural

**Modifiers:**
- Cultural similarity (opposed/neutral/similar/identical): -3 to +4

**Success effects:**
- Gradual cultural shift
- Long-term loyalty to operator faction
- Potential future allies

**Use when:** Long-term strategic positioning, converting populations, building soft power.

---

### 🗡️ Assassination
**Purpose:** Eliminate key figures or leaders
**Base DC:** 18
**Detection Risk:** 40%
**Cooldown:** 168 hours (1 week)

**Modifiers:**
- Target security level (low/medium/high/maximum): +3 to -5

**Success effects:**
- Leadership vacuum
- Target faction significantly weakened
- May trigger succession crisis

**Partial success:**
- Target injured but survived
- Temporary incapacitation

**Use when:** High-risk, high-reward strikes against enemy leadership. Very difficult and detection causes major diplomatic incidents.

---

### 🛡️ Counter-Intelligence
**Purpose:** Detect and disrupt enemy intrigue operations
**Base DC:** 10
**Detection Risk:** 10%
**Cooldown:** 12 hours

**Modifiers:**
- Defensive stance: +2

**Success effects:**
- Active protection network established
- +3 modifier to detect incoming intrigue
- Enemy operations against you have -3 penalty

**Partial success:**
- Basic protection
- +1 to detect incoming intrigue

**Use when:** You suspect enemy intrigue or want to protect valuable assets.

---

## How to Conduct Operations

### Step 1: Launch Operation

**General command:**
```
/intrigue start
  op_type: <operation type>
  operator_faction: <your faction>
  target_faction: <target faction>
  description: <operation description (min 50 chars)>
  scale: <Small/Medium/Large/Massive>
  target_strength: <Weak/Medium/Strong/Very Strong>
  operator_skill: <-5 to +5 modifier>
```

**Sabotage-specific command:**
```
/intrigue sabotage
  operator_faction: <your faction>
  target_faction: <target>
  target_category: <Military/Naval/Exosphere>
  description: <what you're sabotaging (min 50 chars)>
  scale: <Small/Medium/Large/Massive>
  target_strength: <Weak/Medium/Strong/Very Strong>
  operator_skill: <-5 to +5>
```

### Step 2: Roll Your D20

After launching, the bot tells you the Operation ID and Difficulty Class (DC).

Roll a d20 in your preferred method (physical dice, bot, etc.).

### Step 3: Resolve Operation

```
/intrigue resolve
  op_id: <operation ID>
  roll: <your d20 result (1-20)>
```

The system:
1. Calculates modifiers (operator skill, scale, target strength, etc.)
2. Determines success/failure based on total vs DC
3. Rolls for detection
4. Applies effects if successful
5. Posts results to channel

## Resolution Mechanics

### Success Tiers

**Margin = (Roll + Modifiers) - DC**

- **Margin ≥ 10:** Exceptional Success (reduced detection risk)
- **Margin ≥ 5:** Success
- **Margin ≥ 0:** Partial Success (increased detection risk)
- **Margin ≥ -5:** Failure (high detection risk)
- **Margin < -5:** Major Failure (automatic detection)

**Critical Rolls:**
- **Natural 20:** Automatic success, NO detection roll
- **Natural 1:** Automatic detection and failure

### Detection System

After resolving success/failure, the system rolls for detection:

**Detection Roll:** Random % < Detection Risk = Detected

**Detection risk modifiers:**
- Exceptional success: Risk × 0.5
- Partial success: Risk × 1.5
- Failure: Risk × 2.0
- Major failure: Risk = 100% (always detected)

**If detected:**
- Operation exposed
- Operator faction identified
- Target gains casus belli for war
- Diplomatic relations severely damaged
- May trigger immediate war declaration
- Target gains +2 to all actions vs operator for 3 turns

## Modifiers Breakdown

### Universal Modifiers

**Operator Skill:** -5 to +5 (set by GM based on character competence)

**Scale:**
- Small: +2 (easier to hide, less impact)
- Medium: 0 (baseline)
- Large: -2 (harder to execute)
- Massive: -4 (very difficult)

**Target Strength:**
- Weak: +3
- Medium: 0
- Strong: -2
- Very Strong: -4

### Operation-Specific Modifiers

**Rebellion:**
- Target unrest (low/medium/high/critical): -2/0/+2/+4

**Influence:**
- Cultural similarity (opposed/neutral/similar/identical): -3/0/+2/+4

**Assassination:**
- Target security (low/medium/high/maximum): +3/0/-3/-5

**Counter-Intel:**
- Defensive stance: +2

**All operations:**
- Enemy counter-intel active: -3

## Management Commands

### View Active Operations
```
/intrigue list
  faction: <optional faction filter>
```
Shows all pending/active operations.

### View Operation Details
```
/intrigue status
  op_id: <operation ID>
```
Detailed info on specific operation.

### Cancel Operation
```
/intrigue cancel
  op_id: <operation ID>
```
Cancel pending operation (only operator or admin).

### View Gathered Intelligence
```
/intrigue intel
  target_faction: <faction name>
```
Shows intelligence from YOUR successful espionage operations.

### View Detected Enemy Operations
```
/intrigue alerts
  faction: <your faction>
```
Shows enemy operations that were detected targeting you.

## Integration with War System

### Sabotage Effects
Successful sabotage reduces target faction's stats in ALL active wars:
- Targets specific category (military/naval/exosphere)
- Reduction persists until war ends or GM manually restores
- Can turn the tide of losing wars

### Rebellion Effects
Successful rebellion incitement:
- GM can create new war using `/war create` with NPC rebellion
- Use **Insurgent** archetype for rebel forces
- Set to player-driven mode if player controls rebellion
- Original target fights on two fronts

### Espionage Intel
View enemy stats before declaring war:
1. `/intrigue start op_type:Espionage target_faction:Enemy`
2. Resolve successfully
3. `/intrigue intel target_faction:Enemy`
4. See their military capabilities
5. Plan your war strategy accordingly

### Counter-Intel Protection
Active counter-intel makes you harder to sabotage/spy on:
- Enemy operations have -3 penalty
- Increases detection chance
- Defensive factions should maintain counter-intel

## Example Workflow

### Example 1: Sabotage Enemy Navy Before War

```bash
# 1. Launch sabotage operation
/intrigue sabotage
  operator_faction: "Kingdom of Aethel"
  target_faction: "Kraken Empire"
  target_category: Naval
  description: "Covert operatives plant limpet mines on docked capital ships at their main naval base, disguised as dock workers during shift change. Targeting ammunition stores for maximum damage."
  scale: Large
  target_strength: Strong
  operator_skill: 2

# Bot responds: Operation #12 created, DC 16, Detection 40%

# 2. Roll d20 (you get 14)

# 3. Resolve
/intrigue resolve op_id:12 roll:14

# Bot calculates:
# 14 (roll) + 2 (skill) + 0 (scale large) - 2 (strong target) = 14
# 14 vs DC 16 = Margin -2 (FAILURE)
# Detection risk increased to 80%
# Detection roll... DETECTED!

# Result: Operation failed AND detected
# Kraken Empire now knows Aethel tried to sabotage them
# Kraken gains casus belli
# Diplomatic incident
```

### Example 2: Successful Rebellion

```bash
# 1. Launch rebellion
/intrigue start
  op_type: Incite_Rebellion
  operator_faction: "People's Liberation Front"
  target_faction: "Corporate Hegemony"
  description: "Distribute weapons and propaganda to disenfranchised workers in the industrial sector. Coordinate with underground labor unions to stage simultaneous uprisings across three major factory complexes."
  scale: Medium
  target_strength: Medium
  operator_skill: 3

# Bot: Operation #5, DC 16, Detection 50%
# (Assume GM sets target_unrest to "high" giving +2 bonus)

# 2. Roll d20 (you get 17!)

# 3. Resolve
/intrigue resolve op_id:5 roll:17

# Bot calculates:
# 17 (roll) + 3 (skill) + 0 (medium scale) + 0 (medium target) + 2 (high unrest) = 22
# 22 vs DC 16 = Margin +6 (SUCCESS!)
# Detection risk 50%, roll... NOT DETECTED!

# Result: Major uprising triggered!
# Corporate Hegemony suffers -2 to all actions
# GM creates new war: PLF (Insurgent archetype) vs Corporate Hegemony
```

### Example 3: Espionage Intel Gathering

```bash
# 1. Spy on enemy before war
/intrigue start
  op_type: Espionage
  operator_faction: "Star Confederacy"
  target_faction: "Void Collective"
  description: "Deploy deep-cover agents into Void Collective's military command structure. Target communications officer roles to intercept classified force deployment data and strategic readiness reports."
  scale: Small
  target_strength: Strong
  operator_skill: 4

# Bot: Operation #8, DC 14, Detection 13%

# 2. Roll (you get 12)

# 3. Resolve
/intrigue resolve op_id:8 roll:12

# Bot calculates:
# 12 (roll) + 4 (skill) + 2 (small scale) - 2 (strong target) = 16
# 16 vs DC 14 = Margin +2 (SUCCESS!)
# Detection 13%, roll... NOT DETECTED!

# Result: Intel gathered!

# 4. View intel
/intrigue intel target_faction:"Void Collective"

# Bot shows:
# - Exosphere: 45
# - Naval: 30
# - Military: 60
# - Active Wars: None
# - Ongoing Operations: Op #7 (rebellion, small scale)

# Now you know: They're strong on ground but weak in naval!
# Plan your war in naval/space theaters.
```

## Strategy Tips

### Offensive Intrigue
1. **Start with espionage** - Know your enemy before committing
2. **Sabotage key stats** - Reduce their strongest domain before war
3. **Chain operations** - Successful rebellion ties them down, then declare war
4. **Risk management** - High-scale ops are powerful but risky

### Defensive Intrigue
1. **Maintain counter-intel** - Always have active protection
2. **Monitor alerts** - Check `/intrigue alerts` regularly
3. **Retaliate when detected** - Enemy gets caught? Declare war or counter-op

### Cooldown Management
- **Espionage:** 12h (can spam intel gathering)
- **Sabotage:** 24h (pre-plan war timing)
- **Rebellion:** 72h (3 days - use strategically)
- **Assassination:** 168h (1 week - major commitment)

### Scale vs Risk
- **Small scale:** Easier rolls, less impact, lower detection
- **Massive scale:** Harder rolls, huge impact, high detection
- Use small for frequent harassment, massive for war-winning strikes

## GM Tools

### Adjusting Difficulty
Modify operation difficulty based on narrative:
- Heavily guarded target? Increase target_strength
- Inside help? Increase operator_skill
- Target has civil unrest? Set target_unrest to "high" for rebellions

### Creating Rebellion Wars
When rebellion succeeds:
```bash
/war create
  attacker: "Rebel Insurgency"
  defender: "Original Target Faction"

/war set_npc
  war_id: X
  side: Attacker
  archetype: Insurgent
  tech_level: Legacy (usually)
  personality: Aggressive

/war set_mode war_id:X mode:Player-Driven
```

### Responding to Detected Operations
When operation is detected:
- Announce publicly (creates RP opportunity)
- Target faction can declare war (has casus belli)
- Target can launch counter-intrigue operations
- Consider applying temporary penalties to operator faction

## Troubleshooting

**Q: Can't launch operation - cooldown active**
- Each operation type has individual cooldown
- Espionage cooldown doesn't block sabotage, etc.
- Wait for timer or launch different operation type

**Q: Operation detected - what now?**
- Target faction knows you're the aggressor
- They gain casus belli (justification for war)
- Diplomatic relations damaged
- Expect retaliation

**Q: Sabotage succeeded but stats didn't change**
- Check if target faction is in active war
- Sabotage only affects war stats, not base faction stats
- Effect persists for duration of war

**Q: Want to apply intel bonus in war**
- Espionage is for information only
- Use knowledge to make better tactical decisions
- Consider sabotage for actual stat modifications

**Q: Rebellion succeeded but no war created**
- GM must manually create war with `/war create`
- Rebellion creates narrative justification
- Not all rebellions become full wars (GM discretion)
