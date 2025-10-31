# Command Reference - Discord War Tracking Bot

Quick reference for all bot commands. Commands are organized by category.

---

## 📋 Table of Contents

- [War Management](#war-management)
- [War Setup & Configuration](#war-setup--configuration)
- [War Resolution](#war-resolution)
- [War Roster Management](#war-roster-management)
- [Super Units](#super-units)
- [Intrigue Operations](#intrigue-operations)
- [Timers](#timers)

---

## War Management

### `/war create`
Create a new war between two factions.

**Parameters:**
- `attacker` (required) - Name of attacking faction
- `defender` (required) - Name of defending faction
- `mode` (optional) - War mode (conquest/siege/raid)
- `channel` (optional) - Discord channel for war updates

**Example:**
```
/war create attacker:"Kingdom of Aethel" defender:"Kraken Empire"
```

---

### `/war list`
List all active wars.

**Parameters:** None

**Example:**
```
/war list
```

---

### `/war status`
View detailed status of a specific war.

**Parameters:**
- `war_id` (required) - War ID number

**Example:**
```
/war status war_id:1
```

---

### `/war update`
Update war HP/warbar values.

**Parameters:**
- `war_id` (required) - War ID number
- `attacker_hp` (optional) - New attacker HP
- `defender_hp` (optional) - New defender HP
- `warbar` (optional) - New warbar value

**Example:**
```
/war update war_id:1 attacker_hp:80 defender_hp:65
```

---

### `/war end`
End a war and declare a winner.

**Parameters:**
- `war_id` (required) - War ID number
- `winner` (required) - "Attacker", "Defender", or "Stalemate"

**Example:**
```
/war end war_id:1 winner:Attacker
```

---

### `/war next`
Advance to next turn and swap initiative.

**Parameters:**
- `war_id` (required) - War ID number

**Example:**
```
/war next war_id:1
```

---

## War Setup & Configuration

### `/war set_stats`
Set faction military statistics for a war side.

**Parameters:**
- `war_id` (required) - War ID number
- `side` (required) - "Attacker" or "Defender"
- `exosphere` (required) - Space/air forces stat
- `naval` (required) - Naval/water forces stat
- `military` (required) - Ground forces stat

**Example:**
```
/war set_stats war_id:1 side:Attacker exosphere:60 naval:50 military:70
```

---

### `/war set_theater`
Set the war theater (affects stat calculations).

**Parameters:**
- `war_id` (required) - War ID number
- `theater` (required) - "Space", "Naval", "Land", or "Combined Arms"

**Example:**
```
/war set_theater war_id:1 theater:Combined
```

---

### `/war add_modifier`
Add a combat modifier to a war side.

**Parameters:**
- `war_id` (required) - War ID number
- `side` (required) - "Attacker" or "Defender"
- `name` (required) - Modifier name/description
- `value` (required) - Modifier value (positive or negative)
- `duration` (optional) - "Permanent", "Next Resolution", "2 Turns", "3 Turns", "5 Turns"

**Example:**
```
/war add_modifier war_id:1 side:Attacker name:"Fortified Position" value:3 duration:Permanent
```

---

### `/war remove_modifier`
Remove a combat modifier from a war side by name.

**Parameters:**
- `war_id` (required) - War ID number
- `side` (required) - "Attacker" or "Defender"
- `name` (required) - Modifier name to remove

**Example:**
```
/war remove_modifier war_id:1 side:Attacker name:"Fortified Position"
```

---

### `/war set_mode`
Toggle between GM-driven and player-driven war resolution.

**Parameters:**
- `war_id` (required) - War ID number
- `mode` (required) - "GM-Driven (Traditional)" or "Player-Driven (Automatic)"
- `cooldown_hours` (optional, default: 12) - Hours between player resolutions

**Example:**
```
/war set_mode war_id:1 mode:Player-Driven cooldown_hours:12
```

---

### `/war set_npc`
Configure an NPC AI opponent for PvE war.

**Parameters:**
- `war_id` (required) - War ID number
- `side` (required) - "Attacker" or "Defender"
- `archetype` (required) - NPC fighting style
  - "NATO Doctrine" - Combined arms, air superiority
  - "CSAT Doctrine" - Mass mobilization, ground focus
  - "Guerrilla Force" - Asymmetric, hit-and-run
  - "Swarm Doctrine" - Drone-heavy, overwhelming numbers
  - "Elite Force" - Special operations, precision
  - "Defensive Bloc" - Fortifications, attrition
  - "Insurgent/Rebel Force" - Terrorism, rebellion tactics
- `tech_level` (required) - Technology era
  - "Legacy" (0.7x) - Cold War era
  - "Modern" (1.0x) - Contemporary
  - "Advanced" (1.2x) - Near-future
  - "Cutting Edge" (1.4x) - Bleeding-edge 2240
- `personality` (required) - AI behavior
  - "Aggressive" - Offensive focus, high risk
  - "Defensive" - Defensive focus, low risk
  - "Adaptive" - Adjusts based on momentum
  - "Balanced" - Even mix of tactics
  - "Berserker" - All-out attack, no defense

**Example:**
```
/war set_npc war_id:1 side:Defender archetype:Insurgent tech_level:Legacy personality:Aggressive
```

---

## War Resolution

### `/war resolve`
Resolve a turn of war (GM-driven mode only). Opens interactive UI for action selection.

**Parameters:**
- `war_id` (required) - War ID number

**Example:**
```
/war resolve war_id:1
```
*Then use buttons to select main/minor actions for both sides.*

---

### `/war action`
Submit your war action (player-driven mode only).

**Parameters:**
- `war_id` (required) - War ID number
- `main` (required) - Main action
  - "Attack" - Offensive assault
  - "Defend" - Defensive posture (+2 bonus)
  - "Super Unit" - Deploy super unit
- `minor` (required) - Minor action
  - "Prepare Attack" - +1 to next attack
  - "Sabotage" - -1 to enemy roll
  - "Fortify Defense" - +1 to next defense
  - "Heal" - Recover HP
  - "Prepare Super Unit" - Ready super unit for next turn
- `narrative_link` (required) - Discord message link to your 100+ character narrative post
- `roll` (optional) - Your d20 roll (if you rolled already)

**Example:**
```
/war action war_id:1 main:Attack minor:Prepare_Attack narrative_link:https://discord.com/channels/.../... roll:15
```

---

## War Roster Management

### `/war roster add`
Add a player to a war side's roster.

**Parameters:**
- `war_id` (required) - War ID number
- `side` (required) - "Attacker" or "Defender"
- `member` (required) - Discord user to add

**Example:**
```
/war roster add war_id:1 side:Attacker member:@PlayerName
```

---

### `/war roster remove`
Remove a player from a war side's roster.

**Parameters:**
- `war_id` (required) - War ID number
- `side` (required) - "Attacker" or "Defender"
- `participant` (required) - Participant ID or name

**Example:**
```
/war roster remove war_id:1 side:Attacker participant:123456789
```

---

### `/war roster list`
View all participants in a war.

**Parameters:**
- `war_id` (required) - War ID number

**Example:**
```
/war roster list war_id:1
```

---

## Super Units

### `/superunit create`
Create a new super unit with intel system.

**Parameters:**
- `name` (required) - Super unit name
- `max_intel` (required) - Number of intel pieces (1-7)
- `description` (required) - Unit description
- `war_id` (optional) - Associate with specific war

**Example:**
```
/superunit create name:"Titan-Class Dreadnought" max_intel:5 description:"Massive orbital weapons platform with experimental railgun array"
```

---

### `/superunit set_intel`
Set the description for a specific intel piece.

**Parameters:**
- `unit_id` (required) - Super unit ID
- `intel_slot` (required) - Intel slot number (1-7)
- `description` (required) - What this intel reveals

**Example:**
```
/superunit set_intel unit_id:1 intel_slot:1 description:"Railgun targeting system specifications"
```

---

### `/superunit research`
Record a research attempt to unlock intel.

**Parameters:**
- `unit_id` (required) - Super unit ID
- `researcher` (required) - Discord user researching
- `roll` (required) - D20 roll result

**Example:**
```
/superunit research unit_id:1 researcher:@PlayerName roll:18
```
*Grants intel on DC 15+ or Natural 20*

---

### `/superunit grant_intel`
GM manually grants intel to bypass research.

**Parameters:**
- `unit_id` (required) - Super unit ID
- `intel_slot` (required) - Intel slot to unlock (1-7)
- `reason` (required) - Why intel was granted

**Example:**
```
/superunit grant_intel unit_id:1 intel_slot:2 reason:"Captured enemy engineer during raid"
```

---

### `/superunit status`
View super unit intel progress and combat modifier.

**Parameters:**
- `unit_id` (required) - Super unit ID

**Example:**
```
/superunit status unit_id:1
```

---

## Intrigue Operations

### `/intrigue start`
Launch a covert intrigue operation.

**Parameters:**
- `op_type` (required) - Operation type
  - "Espionage" - Gather intelligence (DC 12, 15% detection)
  - "Sabotage" - Damage infrastructure (DC 14, 30% detection)
  - "Incite Rebellion" - Foment uprising (DC 16, 50% detection)
  - "Spread Influence" - Political/religious control (DC 13, 20% detection)
  - "Assassination" - Eliminate leaders (DC 18, 40% detection)
  - "Counter-Intelligence" - Disrupt enemy ops (DC 10, 10% detection)
- `operator_faction` (required) - Your faction name
- `target_faction` (required) - Target faction name
- `description` (required) - Operation description (min 50 characters)
- `scale` (required) - Operation scale
  - "Small" - Low impact, easier (+2 modifier)
  - "Medium" - Standard impact (no modifier)
  - "Large" - High impact, harder (-2 modifier)
  - "Massive" - Extreme impact, very hard (-4 modifier)
- `target_strength` (required) - Target defensive strength
  - "Weak" (+3)
  - "Medium" (no modifier)
  - "Strong" (-2)
  - "Very Strong" (-4)
- `operator_skill` (optional, -5 to +5) - Operator competence modifier

**Example:**
```
/intrigue start op_type:Espionage operator_faction:"Star Confederacy" target_faction:"Void Collective" description:"Deploy deep-cover agents into enemy command structure to intercept classified force deployment data and strategic reports" scale:Small target_strength:Strong operator_skill:3
```

---

### `/intrigue sabotage`
Launch sabotage operation (specialized command with targeting).

**Parameters:**
- `operator_faction` (required) - Your faction name
- `target_faction` (required) - Target faction name
- `target_category` (required) - Infrastructure to sabotage
  - "Military (Ground Forces)"
  - "Naval (Sea/Water Forces)"
  - "Exosphere (Space/Air Forces)"
- `description` (required) - Operation description (min 50 characters)
- `scale` (required) - "Small", "Medium", "Large", "Massive"
- `target_strength` (required) - "Weak", "Medium", "Strong", "Very Strong"
- `operator_skill` (optional, -5 to +5) - Operator modifier

**Example:**
```
/intrigue sabotage operator_faction:"Kingdom of Aethel" target_faction:"Kraken Empire" target_category:Naval description:"Plant limpet mines on docked capital ships at main naval base, disguised as dock workers during shift change. Targeting ammunition stores for maximum damage." scale:Large target_strength:Strong operator_skill:2
```

---

### `/intrigue resolve`
Resolve an intrigue operation with your d20 roll.

**Parameters:**
- `op_id` (required) - Operation ID number
- `roll` (required) - D20 roll result (1-20)

**Example:**
```
/intrigue resolve op_id:5 roll:16
```

---

### `/intrigue list`
List active intrigue operations.

**Parameters:**
- `faction` (optional) - Filter by faction (operator or target)

**Example:**
```
/intrigue list faction:"Star Confederacy"
```

---

### `/intrigue status`
View details of a specific operation.

**Parameters:**
- `op_id` (required) - Operation ID number

**Example:**
```
/intrigue status op_id:5
```

---

### `/intrigue cancel`
Cancel a pending intrigue operation.

**Parameters:**
- `op_id` (required) - Operation ID number

**Example:**
```
/intrigue cancel op_id:5
```

---

### `/intrigue intel`
View intelligence gathered from successful espionage operations.

**Parameters:**
- `target_faction` (required) - Faction to view intel on

**Example:**
```
/intrigue intel target_faction:"Void Collective"
```
*Shows stats, wars, and operations revealed by your espionage*

---

### `/intrigue alerts`
View detected enemy intrigue operations targeting your faction.

**Parameters:**
- `faction` (required) - Your faction name

**Example:**
```
/intrigue alerts faction:"Star Confederacy"
```
*Shows enemy operations that were caught targeting you*

---

## Timers

### `/timer`
Set a timer with notification.

**Parameters:**
- `duration` (required) - Duration string (e.g., "2h", "30m", "1d")
- `description` (required) - What the timer is for

**Example:**
```
/timer duration:2h description:"War resolution deadline"
```

---

## Quick Reference Tables

### War Main Actions
| Action | Effect | Bonus |
|--------|--------|-------|
| Attack | Offensive assault | - |
| Defend | Defensive posture | +2 to roll |
| Super Unit | Deploy super unit | Variable by intel |

### War Minor Actions
| Action | Effect | Bonus |
|--------|--------|-------|
| Prepare Attack | Coordinate next assault | +1 next attack |
| Sabotage | Disrupt enemy | -1 to enemy roll |
| Fortify Defense | Strengthen defenses | +1 next defense |
| Heal | Recover damage | Restore HP |
| Prepare Super Unit | Ready super unit | Enables next turn super unit |

### Intrigue Operation Types
| Type | DC | Detection | Cooldown | Effect |
|------|-----|-----------|----------|--------|
| Espionage | 12 | 15% | 12h | Reveals stats/wars/ops |
| Sabotage | 14 | 30% | 24h | Reduces stats 5-20 |
| Rebellion | 16 | 50% | 72h | Triggers uprising (-2 penalty) |
| Influence | 13 | 20% | 24h | Spreads ideology |
| Assassination | 18 | 40% | 168h | Eliminates leaders |
| Counter-Intel | 10 | 10% | 12h | +3 vs enemy ops |

### NPC Archetypes
| Archetype | Stats Focus | Aggression | Best For |
|-----------|-------------|------------|----------|
| NATO | Balanced (30/30/40) | 0.6 | Modern militaries |
| CSAT | Ground (20/20/60) | 0.5 | Mass armies |
| Guerrilla | Ground (10/10/80) | 0.4 | Resistance |
| Swarm | Space (40/20/40) | 0.8 | Drone forces |
| Elite | Balanced-Pro (30/20/50) | 0.7 | Spec-ops |
| Defensive Bloc | Naval/Ground (20/30/50) | 0.3 | Fortified |
| Insurgent | Ground (5/5/90) | 0.6 | Rebels/terrorists |

### Tech Levels
| Level | Multiplier | Era | Examples |
|-------|------------|-----|----------|
| Legacy | 0.7x | Cold War | AK-47s, T-72 tanks |
| Modern | 1.0x | Contemporary | M4s, Abrams tanks |
| Advanced | 1.2x | Near-future | Smart weapons, camo |
| Cutting Edge | 1.4x | 2240 | Nanoweapons, AI |

### Personalities
| Personality | Aggression Mod | Attack % | Defend % | Behavior |
|-------------|----------------|----------|----------|----------|
| Aggressive | +0.3 | 70% | 20% | Offensive focus |
| Defensive | -0.3 | 20% | 70% | Defensive focus |
| Adaptive | 0.0 | 40% | 40% | Adjusts to momentum |
| Balanced | 0.0 | 50% | 40% | Even mix |
| Berserker | +0.5 | 90% | 5% | All-out attack |

---

## Workflow Examples

### Example 1: Standard GM-Driven War
```bash
# Setup
/war create attacker:"Faction A" defender:"Faction B"
/war set_stats war_id:1 side:Attacker exosphere:60 naval:50 military:70
/war set_stats war_id:1 side:Defender exosphere:40 naval:60 military:65
/war set_theater war_id:1 theater:Combined
/war roster add war_id:1 side:Attacker member:@Player1

# Each turn
/war resolve war_id:1
# (Click UI buttons to select actions, bot auto-resolves)

# End war
/war end war_id:1 winner:Attacker
```

### Example 2: Player-Driven War
```bash
# Setup (same as above, then...)
/war set_mode war_id:1 mode:Player-Driven cooldown_hours:12

# Players submit actions
/war action war_id:1 main:Attack minor:Prepare_Attack narrative_link:<link> roll:15
# (Auto-resolves when both sides submit)
```

### Example 3: PvE War Against Rebellion
```bash
# Setup
/war create attacker:"Player Faction" defender:"Rebel Insurgency"
/war set_npc war_id:1 side:Defender archetype:Insurgent tech_level:Legacy personality:Aggressive
/war set_stats war_id:1 side:Attacker exosphere:60 naval:50 military:70
/war set_theater war_id:1 theater:Land
/war set_mode war_id:1 mode:Player-Driven

# Player submits, NPC auto-responds
/war action war_id:1 main:Attack minor:Sabotage narrative_link:<link> roll:15
```

### Example 4: Espionage → Sabotage → War
```bash
# 1. Gather intel
/intrigue start op_type:Espionage operator_faction:"My Faction" target_faction:"Enemy" description:"Deploy spies into enemy military command..." scale:Small target_strength:Medium operator_skill:2
/intrigue resolve op_id:1 roll:14

# 2. View intel
/intrigue intel target_faction:"Enemy"
# (See they're strong in naval)

# 3. Sabotage their strength
/intrigue sabotage operator_faction:"My Faction" target_faction:"Enemy" target_category:Naval description:"Plant mines on docked ships..." scale:Large target_strength:Strong operator_skill:2
/intrigue resolve op_id:2 roll:16

# 4. Declare war while they're weak
/war create attacker:"My Faction" defender:"Enemy"
```

---

## Tips & Tricks

### For Players
- **Player-driven wars**: Post narrative in RP channel FIRST, then submit action with message link
- **Espionage first**: Always gather intel before major operations
- **Cooldown management**: Espionage (12h) can spam, Assassination (1 week) is strategic
- **Detection risk**: Small scale ops have lower detection chance

### For GMs
- **Stat advantages**: 250%+ = +3, 150%+ = +2, 75%+ = +1
- **Tech levels**: Use Legacy (0.7x) for weaker factions, Cutting Edge (1.4x) for advanced
- **Modifiers**: Add permanent modifiers for fortifications, terrain advantages
- **Player autonomy**: Use player-driven mode to reduce your workload

### For Strategy
- **Dual momentum**: Strategic momentum affects damage (1.0x to 2.0x multiplier)
- **Theater selection**: Choose theater based on your stat advantages
- **Counter-intel**: Maintain protection if you expect enemy intrigue
- **Super units**: Research intel BEFORE deploying (0% intel = -2 penalty!)

---

**For detailed guides, see:**
- [PVE_SYSTEM_GUIDE.md](PVE_SYSTEM_GUIDE.md) - Complete PvE documentation
- [INTRIGUE_SYSTEM_GUIDE.md](INTRIGUE_SYSTEM_GUIDE.md) - Complete Intrigue documentation
- [MEGA_UPDATE_SUMMARY.md](MEGA_UPDATE_SUMMARY.md) - Overall update summary
