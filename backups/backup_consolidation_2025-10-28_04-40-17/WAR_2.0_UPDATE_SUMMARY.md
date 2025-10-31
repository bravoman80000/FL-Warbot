# WAR 2.0 - Massive System Overhaul

This document summarizes all changes in the WAR 2.0 mega-update for the Discord War Tracking Bot.

**Update Date:** October 26, 2025
**Backup Location:** `backups/backup_2025-10-25_21-46-17/`

---

## Overview

WAR 2.0 is a complete overhaul of the war system, adding:
- Dual-track momentum system
- Player-driven automatic resolution
- Super unit mechanics
- PvE AI opponents with learning
- Intrigue operations (espionage, sabotage, rebellion, etc.)
- NPC vs NPC auto-resolution wars
- Command autofill/autocomplete

---

## Phase 1: Dual-Track Momentum System

### Tactical Momentum (±1 to ±3)
- **Old behavior:** Single momentum value that reset when losing
- **New behavior:** Ranges from -3 to +3, only resets when losing
- **Effect:** Adds to combat rolls (+1 to +3)
- **Decay:** Resets to 0 when you lose a battle

### Strategic Momentum (0-10 per side)
- **New system:** Both sides track strategic momentum independently (0-10)
- **Gain/Loss:** Winner gains +1, loser loses -1 per battle
- **Effect:** Multiplies damage dealt (1.0x at 0 momentum, up to 2.0x at 10 momentum)
- **Both sides can have momentum:** Unlike tactical momentum, both attacker and defender can simultaneously have strategic momentum, though it's rare

### Why This Matters
- **Gradual escalation:** Momentum builds over time instead of binary win/lose
- **Comeback potential:** Losing side can recover gradually
- **Strategic depth:** Players must consider both short-term (tactical) and long-term (strategic) advantages

---

## Phase 2: Player-Driven Resolution

### Old System (GM-Driven)
- GMs manually trigger `/war resolve`
- GMs select actions via UI buttons
- Manual process every turn

### New System (Player-Driven)
- Players submit actions via `/war action`
- Both sides must submit before auto-resolution
- 12-hour cooldown before next action submission
- Fully automatic - zero GM intervention

### Commands
- `/war set_mode` - Switch between GM-driven and Player-driven
- `/war action` - Submit combat action (main + minor + narrative + roll)

### How It Works
1. Player uses `/war action` with their narrative link and d20 roll
2. System stores pending action
3. When BOTH sides submit, auto-resolution triggers
4. Results posted to war channel
5. 12-hour cooldown begins

---

## Phase 3: Super Units

### Concept
Super units are powerful one-time abilities that can turn the tide of battle.

### Mechanics
- **Acquired via `/war add_modifier`**: GMs grant super units as rewards
- **One-time use:** Consumed when used in combat
- **Theater-specific:** Exosphere/Naval/Military match war theater
- **Effect:** +2 to combat roll when used

### Super Unit Types

#### Exosphere
- **Orbital Strike Platform** - Kinetic bombardment from orbit
- **Titan-Class Warship** - Flagship with overwhelming firepower
- **Drone Swarm Controller** - AI-coordinated attack drones

#### Naval
- **Supercarrier** - Massive carrier with full air wing
- **Submarine Wolf Pack** - Coordinated sub warfare
- **Naval Bombardment Fleet** - Shore bombardment capability

#### Military
- **Armored Division** - Heavy tank formation
- **Special Forces Battalion** - Elite commandos
- **Artillery Regiment** - Long-range fire support

### Usage
- Players choose "Use Super Unit" as minor action in `/war action`
- System automatically applies +2 modifier
- Super unit removed after use
- Works in both GM-driven and Player-driven modes

---

## Phase 4: PvE AI System

### Overview
Allows one side of a war to be controlled by an adaptive AI opponent.

### NPC Archetypes
Each archetype has unique stats distribution and tactical preferences:

1. **NATO Doctrine** - Combined arms (30/30/40 space/naval/ground), moderate aggression
2. **CSAT Doctrine** - Mass mobilization (20/20/60), overwhelming force
3. **Guerrilla Force** - Asymmetric warfare (10/10/80), hit-and-run
4. **Swarm Doctrine** - Drone swarms (40/20/40), saturation attacks
5. **Elite Force** - Special ops (30/20/50), surgical strikes
6. **Defensive Bloc** - Fortifications (20/30/50), attrition defense
7. **Insurgent/Rebel** - Rebellion (5/5/90), IEDs and ambushes

### Tech Levels
- **Legacy** (0.7x stats) - Cold War era tech
- **Modern** (1.0x stats) - Contemporary 2000s-2020s
- **Advanced** (1.2x stats) - Near-future 2020s-2100s
- **Cutting Edge** (1.4x stats) - 2240 bleeding-edge

### Personalities
- **Aggressive** - 70% attack focus, high risk
- **Defensive** - 70% defend focus, low risk
- **Adaptive** - Adjusts based on momentum
- **Balanced** - Even mix of tactics
- **Berserker** - 90% attack, ignore defense

### Learning System
NPCs adapt based on combat results:
- **After wins:** +0.1 aggression
- **After losses:** -0.2 aggression (become more defensive)
- **Rolling window:** Tracks last 5 battles
- **Decay:** 0.1 per turn

### Setup Commands
- `/war set_npc` - Configure AI opponent (archetype, tech level, personality)
- System auto-generates stats based on config
- NPC auto-responds when player submits action

### How PvE Works
1. Human player submits action via `/war action`
2. NPC immediately generates counter-action
3. NPC generates narrative based on archetype/tech level
4. Combat resolves automatically
5. NPC learning data updates

---

## Phase 5: Intrigue System

### Overview
Covert operations system for espionage, sabotage, rebellion, and more.

### Operation Types

#### 🕵️ Espionage
- **DC:** 12, **Detection:** 15%, **Cooldown:** 12 hours
- **Effect:** Reveals faction stats, wars, ongoing operations

#### 💣 Sabotage
- **DC:** 14, **Detection:** 30%, **Cooldown:** 24 hours
- **Effect:** Reduces target stats (Military/Naval/Exosphere) by 5-20
- **Scales:** Small (-5), Medium (-10), Large (-15), Massive (-20)

#### ⚔️ Incite Rebellion
- **DC:** 16, **Detection:** 50%, **Cooldown:** 72 hours
- **Effect:** Destabilizes territory, GM may create NPC rebellion war
- **Gradual escalation:** Typically requires 2-3 successful ops to trigger full war
- **First success:** Unrest begins
- **Second success:** Uprising intensifies
- **Third success:** Full rebellion (NPC war)

#### 📜 Spread Influence
- **DC:** 13, **Detection:** 20%, **Cooldown:** 24 hours
- **Effect:** Political/religious/ideological control, cultural shift

#### 🗡️ Assassination
- **DC:** 18, **Detection:** 40%, **Cooldown:** 168 hours (1 week)
- **Effect:** Eliminates key figure, creates leadership vacuum

#### 🛡️ Counter-Intelligence
- **DC:** 10, **Detection:** 10%, **Cooldown:** 12 hours
- **Effect:** Protects against enemy intrigue (+3 to detect, -3 to enemy ops)

### Mechanics
- **Roll-based:** d20 + modifiers vs DC
- **Detection risk:** Roll % chance after operation
- **Modifiers:** Operator skill, scale, target strength, cultural similarity, security, etc.
- **Consequences if detected:** Casus belli, diplomatic incident, relations damaged

### Commands
- `/intrigue operation` - Launch covert operation
- `/intrigue list` - View active operations
- `/intrigue resolve` - GM resolves pending operation

---

## Phase 6: NPC vs NPC Auto-Resolution

### Overview
Fully autonomous wars between two AI-controlled factions. Perfect for player-incited rebellions or background conflicts.

### Key Features

#### Auto-Resolution Schedule
- **Default:** Every 12 hours
- **Customizable:** 1-168 hours (1 week max)
- **Automatic:** Generates actions for BOTH NPCs
- **Results:** Posted to war channel automatically

#### Turn Limit
- **Default:** 50 turns maximum
- **Outcome:** Defender auto-wins if limit reached (status quo maintained)
- **Purpose:** Prevents infinite background wars
- **Notification:** GMs notified when limit reached

#### Critical HP Detection
- **Threshold:** When either side could die next turn
- **Calculation:** Max possible damage = 30 × (1.0 + strategic_momentum / 10)
- **Notification:** Pings GM once when HP ≤ max_damage
- **No spam:** Only pings ONCE per war (`critical_hp_notified` flag)

#### Learning System
- Both NPCs adapt independently
- Winners become more aggressive
- Losers become more defensive
- Tracks last 5 battles per NPC

### Commands

#### `/war set_npc`
Configure BOTH sides as NPCs:
```bash
/war set_npc war_id:1 side:Attacker archetype:NATO tech_level:Modern personality:Balanced
/war set_npc war_id:1 side:Defender archetype:Insurgent tech_level:Legacy personality:Aggressive
```

#### `/war set_auto_resolve`
Enable auto-resolution:
```bash
/war set_auto_resolve war_id:1 interval_hours:12 max_turns:50
```

#### `/war stop_auto`
Stop auto-resolution:
```bash
/war stop_auto war_id:1
```

#### `/war escalate`
Convert NPC war to player involvement:
```bash
# Convert to PvE (one side becomes player-controlled)
/war escalate war_id:1 escalation_type:"To PvE" side:Attacker new_mode:"Player-Driven"

# Convert to PvP (both sides become player-controlled)
/war escalate war_id:1 escalation_type:"To PvP" side:Attacker new_mode:"GM-Driven"
```

### How It Works
1. **Hourly scheduler** checks for eligible NPC wars
2. **Interval check:** Has 12 hours passed since last resolution?
3. **Turn limit check:** Has war reached 50 turns?
4. **Action generation:** Both NPCs choose actions based on archetype/personality/learning
5. **Narrative generation:** System creates flavor text for both sides
6. **Combat resolution:** Full combat with rolls, modifiers, damage
7. **Momentum updates:** Both tactical and strategic momentum updated
8. **Learning updates:** Both NPCs adapt based on outcome
9. **Critical HP check:** Ping GM if either side near death
10. **Results posted:** Full combat report to war channel

### Use Cases
- **Player-incited rebellions:** Player uses intrigue to incite rebellion → GM creates NPC war (Empire vs Insurgents) → Runs autonomously
- **Background conflicts:** NPC factions fight while players focus elsewhere
- **World-building:** Create living world with ongoing conflicts
- **Escalation potential:** Use `/war escalate` if players want to get involved

---

## Phase 7: Command Autocomplete

### Overview
All new commands now have autofill/autocomplete for war IDs and other parameters.

### Commands with Autocomplete
- `/war action` - War ID autofill
- `/war set_stats` - War ID autofill
- `/war set_theater` - War ID autofill
- `/war add_modifier` - War ID autofill
- `/war remove_modifier` - War ID autofill
- `/war set_mode` - War ID autofill
- `/war set_npc` - War ID autofill
- `/war set_auto_resolve` - War ID autofill
- `/war stop_auto` - War ID autofill
- `/war escalate` - War ID autofill
- `/time timer_cancel` - Timer ID autofill with descriptions

### How It Works
- War IDs show as: `#1: Faction A vs Faction B`
- Timer IDs show as: `Timer #1: Reminder description`
- Searches current text as you type
- Maximum 25 results shown

---

## Timer Notification Fix

### Issue
Timer notifications were failing to @ mention users properly.

### Fix
- Updated timer notification system to properly ping users
- Fixed mention format in timer embeds

---

## Backward Compatibility

### Data Migration
All existing wars automatically migrate to new structure:

1. **Old single-side NPC config** → New dual-side structure
2. **Old `npc_controlled` fields** → New `npc_config` structure
3. **Missing fields** → Auto-populated with defaults
4. **Tactical momentum** → Migrated from old `momentum` field
5. **Strategic momentum** → Initialized at 0 for both sides

### Existing Wars
- **Will not break:** All existing wars compatible
- **Auto-migrated:** First load applies all new defaults
- **No data loss:** Old fields preserved during migration
- **Seamless upgrade:** No GM action required

---

## Documentation

### Updated Guides
- **PVE_SYSTEM_GUIDE.md** - Complete PvE and NPC vs NPC guide
- **INTRIGUE_SYSTEM_GUIDE.md** - Intrigue operations guide
- **WAR_2.0_UPDATE_SUMMARY.md** - This document

### New Sections
- NPC vs NPC setup workflow
- Auto-resolution features
- War escalation system
- Rebellion gradual escalation
- Critical HP notifications
- Turn limit mechanics

---

## Testing Checklist

Before deploying to production, test:

### Basic War Functions
- [ ] Create war
- [ ] View war status
- [ ] Update war
- [ ] End war

### Dual Momentum
- [ ] Tactical momentum increases on win
- [ ] Tactical momentum resets on loss
- [ ] Strategic momentum increases for winner (+1)
- [ ] Strategic momentum decreases for loser (-1)
- [ ] Both sides can have strategic momentum simultaneously

### Player-Driven Resolution
- [ ] Set war to player-driven mode
- [ ] Both sides submit actions
- [ ] Auto-resolution triggers
- [ ] 12-hour cooldown enforced
- [ ] Results posted to channel

### Super Units
- [ ] Add super unit via `/war add_modifier`
- [ ] Use super unit in combat
- [ ] Super unit removed after use
- [ ] +2 modifier applied correctly

### PvE AI
- [ ] Configure NPC via `/war set_npc`
- [ ] Stats auto-generated based on archetype/tech level
- [ ] NPC auto-responds to player action
- [ ] NPC narrative matches archetype/tech level
- [ ] NPC learning data updates after combat

### Intrigue
- [ ] Launch operation via `/intrigue operation`
- [ ] Roll vs DC calculated correctly
- [ ] Detection roll occurs
- [ ] Effects applied (sabotage reduces stats, espionage reveals info)
- [ ] Cooldown enforced

### NPC vs NPC
- [ ] Configure both sides as NPCs
- [ ] Enable auto-resolution
- [ ] Hourly scheduler triggers resolution
- [ ] Both NPCs generate actions
- [ ] Combat resolves automatically
- [ ] Results posted to channel
- [ ] Critical HP notification works (only once)
- [ ] Turn limit ends war (defender wins)
- [ ] War escalation converts to player control

### Autocomplete
- [ ] War ID autocomplete works on all commands
- [ ] Timer ID autocomplete works
- [ ] Search/filter works as you type

---

## Known Limitations

1. **One scheduler instance:** Only one bot instance should run to avoid duplicate resolutions
2. **Channel permissions:** Bot needs send permissions in war channels
3. **Intrigue gradual escalation:** Rebellion escalation is manual (GM creates war after 2-3 ops)
4. **NPC personality limits:** 5 personalities, may want more variety in future
5. **Turn limit only for NPC wars:** Player wars have no automatic end

---

## Future Enhancements

Potential features for future updates:

1. **Diplomacy system** - Peace treaties, alliances, trade agreements
2. **Economic system** - Resource management, war costs
3. **More NPC archetypes** - Pirate fleets, corporate armies, alien swarms
4. **Advanced intrigue** - Multi-stage operations, operation chains
5. **War theaters** - Multiple fronts in single war
6. **Historical replay** - View past battles in detail
7. **Statistics dashboard** - Faction win rates, player performance
8. **Custom super units** - Player-designed unique abilities

---

## Credits

**System Design:** Bravo + Co-GMs
**Development:** Claude (Anthropic)
**Testing:** Bravo's NRP Community
**Lore Basis:** Children of Dusk (heavily modified)

**Original Motivation:** Escape from problematic previous GM who ruined multiple NRP attempts. This bot exists to automate fair war resolution and prevent GM abuse.

---

## Support

For issues, questions, or feature requests:
- Check documentation in repo
- Ask in NRP Discord
- File issue on GitHub (if applicable)

**Backup restored from:** `backups/backup_2025-10-25_21-46-17/`

---

**WAR 2.0 Status:** ✅ Complete and ready for deployment
