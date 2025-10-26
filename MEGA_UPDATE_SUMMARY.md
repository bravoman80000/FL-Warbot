# MEGA UPDATE SUMMARY - Complete War System Overhaul

This document summarizes the massive update to the Discord War Tracking Bot, including war system improvements, PvE AI, and the new Intrigue system.

## 🎯 Update Goals

1. ✅ Fix timer notifications not @mentioning users
2. ✅ Improve "clunky" war system with dual momentum
3. ✅ Add player-driven war resolution
4. ✅ Implement Super Unit tracking with intel system
5. ✅ Create PvE AI opponents for solo play
6. ✅ Add comprehensive Intrigue system (espionage, sabotage, rebellion, etc.)

## 📦 What's New

### Phase 1: Enhanced War Data Structure
- **Stats tracking**: Exosphere, Naval, Military stats for both sides
- **Theater system**: Space, Naval, Land, Combined Arms
- **Modifiers**: Temporary and permanent combat bonuses/penalties
- **Dual momentum**: Tactical (±3, resets) + Strategic (0-10, cumulative)

### Phase 2: GM-Driven Resolution Improvements
- **Action selection UI**: Interactive buttons and dropdowns
- **Auto-modifier calculation**: Based on stats, theater, and actions
- **Main actions**: Attack, Defend, Super Unit
- **Minor actions**: Prepare Attack, Sabotage, Fortify Defense, Heal, Prepare Super Unit

### Phase 3: Player-Driven Resolution
- **`/war action` command**: Players submit actions with narratives
- **Narrative enforcement**: 100+ character posts required with Discord message links
- **Cooldown system**: Configurable hours between resolutions
- **Auto-resolution**: Combat resolves when both sides submit

### Phase 4: Super Unit System
- **Intel tracking**: 1-7 intel pieces unlockable through research
- **Research mechanics**: DC 15 or nat 20 grants intel
- **Combat modifiers**: +2 (100%), 0 (50-99%), -2 (<50%) based on intel
- **GM approval**: Super Units require GM authorization (Option A)

### Phase 5: PvE AI Opponents
- **7 Archetypes**: NATO, CSAT, Guerrilla, Swarm, Elite, Defensive Bloc, **Insurgent**
- **4 Tech Levels**: Legacy (0.7x), Modern (1.0x), Advanced (1.2x), Cutting Edge (1.4x)
- **5 Personalities**: Aggressive, Defensive, Adaptive, Balanced, Berserker
- **Auto-response**: NPC automatically responds to player actions
- **Learning system**: Adapts tactics based on wins/losses

### Phase 6: Intrigue System
- **6 Operation Types**: Espionage, Sabotage, Rebellion, Influence, Assassination, Counter-Intel
- **Roll-based resolution**: D20 + modifiers vs DC
- **Detection system**: Risk of getting caught with diplomatic consequences
- **War integration**: Sabotage affects war stats, rebellion triggers wars
- **Intel gathering**: Espionage reveals enemy capabilities

## 📁 New Files Created

### Core Systems
1. **warbot/core/combat.py** - Modifier calculation and combat logic
2. **warbot/core/superunit_manager.py** - Super Unit data management
3. **warbot/core/npc_ai.py** - PvE AI decision-making and learning
4. **warbot/core/npc_narratives.py** - NPC action narrative generation
5. **warbot/core/intrigue_manager.py** - Intrigue operation data management
6. **warbot/core/intrigue_operations.py** - Intrigue mechanics and resolution

### Commands
7. **warbot/commands/superunit_commands.py** - `/superunit` command group
8. **warbot/commands/intrigue_commands.py** - `/intrigue` command group

### Documentation
9. **PVE_SYSTEM_GUIDE.md** - Complete PvE system documentation
10. **INTRIGUE_SYSTEM_GUIDE.md** - Complete Intrigue system documentation
11. **MEGA_UPDATE_SUMMARY.md** - This file!

## 🔧 Modified Files

### warbot/core/scheduler.py
**Changes:** Fixed timer notifications
- Added `AllowedMentions` to war stagnation alerts
- Added `AllowedMentions` to time advancement announcements

### warbot/core/data_manager.py
**Changes:** Backward compatibility for new war fields
- Added `apply_war_defaults()` function
- Auto-migrates existing wars to new structure
- Adds npc_config, stats, theater, modifiers, dual momentum, etc.

### warbot/core/utils.py
**Changes:** Dual momentum system
- `update_dual_momentum()` - Updates both tactical and strategic momentum
- `calculate_damage_multiplier()` - Converts strategic momentum to damage
- `format_tactical_momentum()` - Visual rendering with emoji
- `format_strategic_momentum()` - Strategic momentum display

### warbot/commands/war_commands.py
**Major Changes:**
- Added `/war set_stats` - Set faction stats
- Added `/war set_theater` - Set war theater
- Added `/war add_modifier` - Add combat modifiers
- Added `/war remove_modifier` - Remove modifiers
- Added `/war set_mode` - Toggle GM vs player-driven
- Added `/war set_npc` - Configure PvE AI opponent
- Added `/war action` - Player action submission
- Updated `/war resolve` - New action selection UI
- Added `_auto_resolve_player_war()` - Player-driven resolution
- Added NPC auto-response logic
- Added NPC learning data updates

## 🎮 New Commands Reference

### War Commands
```bash
/war set_stats <war_id> <side> <exosphere> <naval> <military>
/war set_theater <war_id> <theater>
/war add_modifier <war_id> <side> <name> <value> [duration]
/war remove_modifier <war_id> <side> <name>
/war set_mode <war_id> <mode> [cooldown_hours]
/war set_npc <war_id> <side> <archetype> <tech_level> <personality>
/war action <war_id> <main> <minor> <narrative_link> [roll]
```

### Super Unit Commands
```bash
/superunit create <name> <max_intel> <description> [war_id]
/superunit set_intel <unit_id> <intel_slot> <description>
/superunit research <unit_id> <researcher> <roll>
/superunit grant_intel <unit_id> <intel_slot> <reason>
/superunit status <unit_id>
```

### Intrigue Commands
```bash
/intrigue start <op_type> <operator_faction> <target_faction> <description> <scale> <target_strength> [operator_skill]
/intrigue sabotage <operator_faction> <target_faction> <target_category> <description> <scale> <target_strength> [operator_skill]
/intrigue resolve <op_id> <roll>
/intrigue list [faction]
/intrigue status <op_id>
/intrigue cancel <op_id>
/intrigue intel <target_faction>
/intrigue alerts <faction>
```

## 🔄 Migration & Backward Compatibility

### Existing Wars Are Safe! ✅

When you restart the bot:
1. All existing wars automatically get new fields with safe defaults
2. Old momentum values migrate to tactical_momentum
3. NPC system defaults to disabled
4. Stats default to 0 (no stat bonuses until set)
5. Wars remain in GM-driven mode
6. Everything continues working as before

**No action required** - but you can enhance existing wars:
```bash
# Add stats to existing war
/war set_stats war_id:1 side:Attacker exosphere:50 naval:50 military:50

# Set theater
/war set_theater war_id:1 theater:Land

# Enable player-driven (optional)
/war set_mode war_id:1 mode:Player-Driven cooldown_hours:12
```

## 🎯 Key Features Deep Dive

### Dual-Track Momentum System

**Tactical Momentum** (±1 to ±3):
- Resets when momentum shifts
- Affects roll modifiers
- Visual: ⚡⚡⚡ Attacker (+3)

**Strategic Momentum** (0-10 per side):
- Cumulative throughout war
- Affects damage multiplier (1.0x to 2.0x)
- Represents long-term strategic advantage

**Example:**
- Attacker wins: Tactical +1, Strategic (attacker) +1
- Attacker wins again: Tactical +2, Strategic (attacker) +2
- Defender wins: Tactical -1 (reset and flip), Strategic (defender) +1
- Strategic momentum creates lasting impact even after tactical reversals

### Auto-Modifier Calculation

System automatically calculates:
1. **Stat advantages** - Based on theater and stat ratios
   - 250%+ advantage: +3
   - 150%+ advantage: +2
   - 75%+ advantage: +1
2. **Permanent modifiers** - From `/war add_modifier`
3. **Main action bonuses** - Defend: +2
4. **Minor action bonuses** - Prepare Attack: +1, Fortify: +1 to next defense
5. **Tactical momentum** - Current momentum value

**No more manual modifier tracking!**

### Player-Driven Resolution

**Requirements:**
- War set to player-driven mode
- Both sides submit actions via `/war action`
- Narrative post must be 100+ characters
- Must provide Discord message link
- Cooldown respected (default 12 hours)

**Flow:**
1. Player 1 uses `/war action` with narrative link
2. If opponent is NPC → auto-generates NPC action → resolves immediately
3. If opponent is player → waits for opponent submission
4. When both submitted → auto-resolves and posts results

### NPC AI Intelligence

**Archetype determines:**
- Stat distribution (Insurgent: 90% military, Swarm: 40% exosphere)
- Preferred actions (Guerrilla: defend + sabotage)
- Base aggression (Berserker: 0.8, Defensive Bloc: 0.3)

**Personality modifies:**
- Aggression level (Aggressive: +0.3, Defensive: -0.3)
- Action bias (Aggressive: 70% attack)
- Special behaviors (Adaptive: adjusts based on momentum)

**Learning adapts:**
- After wins: +0.1 aggression
- After losses: -0.2 aggression
- Rolling 5-battle memory
- Gradually forgets old results

### Intrigue Operation Resolution

**Success Formula:**
```
Total = D20 + Operator Skill + Scale Mod + Target Strength Mod + Special Mods
Success if Total ≥ DC
```

**Detection Formula:**
```
Detection Risk = Base Risk × Success Modifier
Random Roll < Detection Risk = Detected!
```

**Consequences of Detection:**
- Operation exposed
- Casus belli for target
- Diplomatic crisis
- +2 to target's actions vs operator for 3 turns
- May trigger immediate war

## 🚀 Quick Start Guide

### Setting Up a GM-Driven War
```bash
# 1. Create war
/war create attacker:"Faction A" defender:"Faction B"

# 2. Set stats
/war set_stats war_id:1 side:Attacker exosphere:60 naval:50 military:70
/war set_stats war_id:1 side:Defender exosphere:40 naval:60 military:65

# 3. Set theater
/war set_theater war_id:1 theater:Combined

# 4. Add participants
/war roster add war_id:1 side:Attacker member:@Player1
/war roster add war_id:1 side:Defender member:@Player2

# 5. Resolve with action UI
/war resolve war_id:1
# Click buttons to select actions, bot auto-calculates and resolves
```

### Setting Up a Player-Driven War
```bash
# Steps 1-4 same as above, then:

# 5. Enable player-driven mode
/war set_mode war_id:1 mode:Player-Driven cooldown_hours:12

# 6. Players submit actions
/war action war_id:1 main:Attack minor:Prepare_Attack narrative_link:<link> roll:15

# Auto-resolves when both sides submit!
```

### Setting Up a PvE War
```bash
# 1. Create war
/war create attacker:"Player Faction" defender:"Rebel Insurgency"

# 2. Configure NPC (auto-generates stats!)
/war set_npc war_id:1 side:Defender archetype:Insurgent tech_level:Legacy personality:Aggressive

# 3. Set player stats
/war set_stats war_id:1 side:Attacker exosphere:60 naval:50 military:70

# 4. Set theater and mode
/war set_theater war_id:1 theater:Land
/war set_mode war_id:1 mode:Player-Driven

# 5. Add players
/war roster add war_id:1 side:Attacker member:@Player1

# 6. Players submit, NPC auto-responds!
/war action war_id:1 main:Attack minor:Sabotage narrative_link:<link> roll:15
```

### Conducting Intrigue Operations
```bash
# 1. Launch espionage
/intrigue start op_type:Espionage operator_faction:"My Faction" target_faction:"Enemy Faction" description:"Deploy spies into enemy command structure to intercept classified military data and force deployment information." scale:Small target_strength:Medium operator_skill:2

# Bot responds: Operation #1 created, DC 12, Detection 13%

# 2. Roll d20 (you get 14)

# 3. Resolve
/intrigue resolve op_id:1 roll:14

# Bot: Success! Intel gathered, not detected.

# 4. View intel
/intrigue intel target_faction:"Enemy Faction"
# Shows enemy stats, wars, operations

# 5. Plan sabotage based on intel
/intrigue sabotage operator_faction:"My Faction" target_faction:"Enemy Faction" target_category:Naval description:"Limpet mines planted on docked capital ships at main naval base during shift change." scale:Large target_strength:Strong operator_skill:2

# 6. Resolve sabotage
/intrigue resolve op_id:2 roll:16
# Success! Enemy naval reduced by 15 points in all active wars!
```

## 📊 System Comparison

### Before vs After

| Feature | Before | After |
|---------|---------|-------|
| Momentum | Single track, ping-pongs | Dual track (tactical + strategic) |
| Stats | Not tracked | Exosphere/Naval/Military per side |
| Modifiers | Manual tracking | Auto-calculated from stats, actions, theater |
| Resolution | GM manual | GM UI + Player-driven + PvE AI |
| Player autonomy | GM dependent | Players can resolve wars independently |
| PvE capability | None | Full AI with 7 archetypes, 5 personalities |
| Intrigue | None | 6 operation types with detection risk |
| Super Units | Basic tracking | Intel system with research mechanics |
| Timers | Broken @ mentions | Fixed with AllowedMentions |

## 🎨 Archetypes at a Glance

| Archetype | Focus | Stats | Style | Best For |
|-----------|-------|-------|-------|----------|
| NATO | Combined arms, air power | Balanced | Professional coordination | Conventional modern militaries |
| CSAT | Mass mobilization | Ground-heavy | Overwhelming force | Large authoritarian states |
| Guerrilla | Asymmetric warfare | 80% military | Hit-and-run | Resistance movements |
| Swarm | Drone warfare | 40% exosphere | Saturation attacks | AI-driven factions |
| Elite | Special operations | Balanced-professional | Surgical strikes | Spec-ops focused nations |
| Defensive Bloc | Fortifications | Naval/military | Attrition defense | Defensive coalitions |
| **Insurgent** | Rebellion/terrorism | 90% military | IEDs, ambushes | Rebels, terrorists, incited wars |

## 🎭 Operation Types at a Glance

| Operation | DC | Detection | Cooldown | Effect |
|-----------|-----|-----------|----------|--------|
| Espionage | 12 | 15% | 12h | Reveals enemy stats/wars/ops |
| Sabotage | 14 | 30% | 24h | Reduces enemy stats by 5-20 |
| Rebellion | 16 | 50% | 72h | Triggers uprising, -2 penalty |
| Influence | 13 | 20% | 24h | Spreads ideology/religion |
| Assassination | 18 | 40% | 168h | Eliminates leaders |
| Counter-Intel | 10 | 10% | 12h | +3 vs enemy ops, detection boost |

## 🐛 Known Limitations

1. **Intrigue-War Integration**: Sabotage only affects active wars, not base faction stats
2. **NPC Super Units**: NPCs don't auto-deploy super units (GM must manually assign)
3. **Rebellion Wars**: Must be manually created by GM after successful rebellion intrigue
4. **Intel Decay**: Espionage intel doesn't expire (could become outdated)
5. **Multi-Faction Wars**: System designed for 1v1, multi-faction wars not supported

## 🔮 Future Expansion Ideas

- **Diplomacy System**: Treaties, alliances, trade agreements
- **Economy**: Resource management affecting war capabilities
- **Tech Tree**: Research unlocking new capabilities
- **Map System**: Territory control and movement
- **Multi-Faction Wars**: 2v2 or free-for-all conflicts
- **Automated Tournaments**: Bracketed war competitions
- **War Crimes**: Special intrigue operations with severe consequences
- **Spy Networks**: Persistent agents that provide ongoing intel

## 📚 Documentation Index

- **[PVE_SYSTEM_GUIDE.md](PVE_SYSTEM_GUIDE.md)** - Complete PvE AI documentation
- **[INTRIGUE_SYSTEM_GUIDE.md](INTRIGUE_SYSTEM_GUIDE.md)** - Complete Intrigue system documentation
- **[MEGA_UPDATE_SUMMARY.md](MEGA_UPDATE_SUMMARY.md)** - This file, overall summary
- **Backup**: `backups/backup_2025-10-25_21-46-17/` - Pre-update backup for safety

## 🙏 Credits

Built for a 2240 cyberpunk TTRPG setting with Cold War to bleeding-edge tech.
Designed to reduce GM workload while maintaining narrative quality.
Supports both player-driven autonomy and GM-controlled precision.

**Have fun conquering the stars! 🚀**
