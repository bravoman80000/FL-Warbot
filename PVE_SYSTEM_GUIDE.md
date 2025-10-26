# PvE War System Guide

This guide explains how the new PvE (Player vs Environment) and NPC vs NPC war systems work in the Discord War Tracking Bot.

## Overview

The PvE system allows GMs to create wars where one or both sides are controlled by AI opponents:

- **PvE (Player vs Environment)**: One side is human players, the other is NPC. When a player submits their action via `/war action`, the NPC automatically responds with its own action and narrative, then combat resolves immediately.

- **NPC vs NPC (Environment vs Environment)**: Both sides are NPCs. The war auto-resolves on a schedule (default 12 hours) without GM intervention. Perfect for player-incited rebellions or background conflicts.

## Setting Up a PvE War

### 1. Create the War
Use `/war create` as normal to set up the war structure.

### 2. Configure the NPC Opponent
Use `/war set_npc` to configure the AI:

```
/war set_npc
  war_id: <war ID>
  side: <Attacker or Defender>
  archetype: <see archetypes below>
  tech_level: <see tech levels below>
  personality: <see personalities below>
```

This command will:
- Automatically generate stats based on archetype and tech level
- Set up the NPC to auto-respond when players submit actions
- Display an info card showing the NPC configuration

### 3. Set War to Player-Driven Mode
```
/war set_mode
  war_id: <war ID>
  mode: Player-Driven (Automatic)
  cooldown_hours: 12
```

### 4. Add Player Participants
Use `/war roster add` to add human players to the **non-NPC side**.

## How PvE Combat Works

1. **Player submits action**: Human player uses `/war action` with their narrative, roll, and action choices
2. **NPC auto-responds**: System immediately generates:
   - NPC action selection (based on archetype, personality, and learning data)
   - NPC narrative (flavor text matching archetype and tech level)
   - NPC d20 roll
3. **Auto-resolution**: Combat resolves immediately and posts results to war channel
4. **NPC learns**: After each battle, NPC adjusts tactics based on win/loss record

## NPC Archetypes

### NATO Doctrine
- **Focus**: Combined arms, air superiority
- **Stats**: Balanced (30% space, 30% naval, 40% ground)
- **Style**: Professional, coordinated strikes
- **Aggression**: Moderate (0.6)

### CSAT Doctrine
- **Focus**: Mass mobilization, ground superiority
- **Stats**: Ground-heavy (20% space, 20% naval, 60% ground)
- **Style**: Overwhelming force, attrition warfare
- **Aggression**: Moderate (0.5)

### Guerrilla Force
- **Focus**: Asymmetric warfare, hit-and-run
- **Stats**: Ground-only (10% space, 10% naval, 80% ground)
- **Style**: Ambushes, sabotage, evasion
- **Aggression**: Low (0.4)

### Swarm Doctrine
- **Focus**: Drone swarms, overwhelming numbers
- **Stats**: Air/space dominant (40% space, 20% naval, 40% ground)
- **Style**: Saturation attacks, cheap units
- **Aggression**: High (0.8)

### Elite Force
- **Focus**: Special operations, precision strikes
- **Stats**: Balanced-professional (30% space, 20% naval, 50% ground)
- **Style**: Surgical strikes, quality over quantity
- **Aggression**: High (0.7)

### Defensive Bloc
- **Focus**: Fortifications, attrition defense
- **Stats**: Naval/ground (20% space, 30% naval, 50% ground)
- **Style**: Static defense, prepared positions
- **Aggression**: Low (0.3)

### Insurgent/Rebel Force
- **Focus**: Rebellion, terrorism, incited conflicts
- **Stats**: Ground-only (5% space, 5% naval, 90% ground)
- **Style**: IEDs, ambushes, blend into population
- **Aggression**: Moderate (0.6)
- **Perfect for**: Rebellions, terrorist cells, foreign-incited wars

## Tech Levels

### Legacy (0.7x stats)
- **Era**: Cold War (1960s-1990s)
- **Examples**: AK-47s, T-72 tanks, early jets, basic radio comms

### Modern (1.0x stats)
- **Era**: Contemporary (2000s-2020s)
- **Examples**: M4 carbines, Abrams tanks, drones, digital comms

### Advanced (1.2x stats)
- **Era**: Near-future (2020s-2100s)
- **Examples**: Smart weapons, active camo, AI targeting, cyber warfare

### Cutting Edge (1.4x stats)
- **Era**: 2240 bleeding-edge
- **Examples**: Nanoweapons, neural interfaces, orbital strikes, full AI integration

## Personalities

### Aggressive
- **Style**: High risk, offensive focus
- **Bias**: 70% attack, 20% defend, 10% super unit
- **Modifier**: +0.3 aggression

### Defensive
- **Style**: Low risk, defensive focus
- **Bias**: 20% attack, 70% defend, 10% super unit
- **Modifier**: -0.3 aggression

### Adaptive
- **Style**: Adjusts based on momentum
- **Bias**: 40% attack, 40% defend, 20% super unit
- **Special**: Becomes more aggressive when winning, more defensive when losing

### Balanced
- **Style**: Even mix of tactics
- **Bias**: 50% attack, 40% defend, 10% super unit
- **Modifier**: No change

### Berserker
- **Style**: All-out attack, ignore defense
- **Bias**: 90% attack, 5% defend, 5% super unit
- **Modifier**: +0.5 aggression

## NPC Learning System

NPCs adapt their tactics over time:

- **After wins**: Become slightly more aggressive (+0.1)
- **After losses**: Become more defensive (-0.2)
- **Rolling window**: Tracks last 5 battles
- **Decay**: Old results gradually fade (0.1 per turn)
- **Adaptive personality**: Adjusts even more based on current momentum

## Example Workflow: PvE War

```bash
# 1. Create war
/war create attacker:"Player Faction" defender:"Rebel Insurgency"

# 2. Configure NPC
/war set_npc war_id:1 side:Defender archetype:Insurgent tech_level:Legacy personality:Aggressive

# 3. Set stats for player side
/war set_stats war_id:1 side:Attacker exosphere:60 naval:50 military:70

# 4. Set theater
/war set_theater war_id:1 theater:Land

# 5. Enable player-driven mode
/war set_mode war_id:1 mode:Player-Driven cooldown_hours:12

# 6. Add human players
/war roster add war_id:1 side:Attacker member:@PlayerName

# 7. Players submit actions (NPC auto-responds!)
/war action war_id:1 main:Attack minor:Prepare_Attack narrative_link:<message link> roll:15
```

## Setting Up NPC vs NPC Wars

Perfect for player-incited rebellions or background conflicts that run autonomously.

### 1. Create the War
```bash
/war create attacker:"Imperial Forces" defender:"Rebel Insurgents"
```

### 2. Configure BOTH Sides as NPCs
```bash
# Configure attacker
/war set_npc war_id:1 side:Attacker archetype:NATO tech_level:Modern personality:Balanced

# Configure defender
/war set_npc war_id:1 side:Defender archetype:Insurgent tech_level:Legacy personality:Aggressive
```

### 3. Enable Auto-Resolution
```bash
/war set_auto_resolve war_id:1 interval_hours:12 max_turns:50
```

This will:
- Auto-resolve combat every 12 hours
- Generate actions for BOTH NPCs
- Post results to war channel
- Run for maximum 50 turns (then defender wins)
- Ping GM when either side reaches critical HP

### 4. Optional: Escalate to Player Involvement
If the conflict escalates and players want to get involved:
```bash
# Convert to PvE (one side becomes player-controlled)
/war escalate war_id:1 escalation_type:"To PvE" side:Attacker new_mode:"Player-Driven"

# Or convert to PvP (both sides become player-controlled)
/war escalate war_id:1 escalation_type:"To PvP" side:Attacker new_mode:"GM-Driven"
```

### 5. Stop Auto-Resolution
```bash
/war stop_auto war_id:1
```

## NPC vs NPC Features

### Auto-Resolution Schedule
- Default: Every 12 hours
- Customizable: 1-168 hours (1 week max)
- Combat generates automatically for both sides
- Results posted to war channel

### Turn Limit
- Default: 50 turns maximum
- Defender auto-wins if limit reached (status quo maintained)
- Prevents infinite wars
- GMs notified when limit reached

### Critical HP Notifications
- System calculates max possible damage based on momentum
- Pings GM when either side could die next turn
- Only pings ONCE per war (no spam)
- Threshold: Between max damage and 1 HP

### Learning System
- Both NPCs adapt tactics based on win/loss
- Winners become more aggressive (+0.1)
- Losers become more defensive (-0.2)
- Tracks last 5 battles per NPC

### War Escalation
- GMs can convert NPC wars to PvE or PvP mid-conflict
- Use `/war escalate` command
- Auto-resolution stops automatically
- Players can be added via `/war roster add`

## Tips for GMs

1. **Match archetype to lore**: Use Insurgent for rebellions, NATO for professional armies, Swarm for drone-heavy factions
2. **Tech level matters**: Legacy forces are 30% weaker than Cutting Edge - use this for asymmetric conflicts
3. **Personality creates variety**: Same archetype with different personalities plays very differently
4. **Let NPCs learn**: Over multiple battles, NPCs will adapt to player tactics
5. **Use player-driven mode**: Removes GM burden while maintaining narrative quality

## Troubleshooting

**Q: NPC isn't responding to player actions (PvE)**
- Check that `/war set_npc` was used and `enabled: true`
- Verify war is in `player_driven` mode via `/war set_mode`
- Check that the NPC is configured for the correct side (attacker or defender)

**Q: NPC vs NPC war isn't auto-resolving**
- Check that `/war set_auto_resolve` was used
- Verify BOTH sides are configured as NPCs via `/war set_npc`
- Check that enough time has passed (default 12 hours between resolutions)
- View war status with `/war status` to see auto-resolve settings

**Q: NPC stats seem too high/low**
- Manually adjust with `/war set_stats` after using `/war set_npc`
- Or use different tech level (Legacy = weaker, Cutting Edge = stronger)

**Q: NPC narrative is too generic**
- Each archetype has unique narrative templates
- Narratives change based on actions (attack vs defend vs super unit)
- Consider using different archetype if flavor doesn't match faction

**Q: Want to disable NPC mid-war**
- For PvE: You can't directly disable, but you can change war back to `gm_driven` mode
- Then use `/war resolve` manually with action selection UI
- For NPC vs NPC: Use `/war stop_auto` to stop auto-resolution
- Or use `/war escalate` to convert to player involvement

**Q: Want to convert NPC war to player war**
- Use `/war escalate` command to convert NPC sides to player control
- Choose PvE (one side) or PvP (both sides)
- Then add players with `/war roster add`

**Q: NPC war reached turn limit**
- Default is 50 turns, defender wins (status quo)
- This is by design to prevent infinite wars
- War ends automatically, GMs are notified
- Can be customized with `max_turns` parameter in `/war set_auto_resolve`
