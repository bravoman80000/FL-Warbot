# 🚀 OPERATION GREENLIGHT 2.0 - In Progress

**Status:** Phase 2 Complete - Ready for Incremental Testing
**Date:** 2025-10-30

---

## ✅ Completed Phases

### Phase 1: Unified Sub-Bar System ✅
**File Created:** [warbot/core/subbar_manager.py](warbot/core/subbar_manager.py:1) (550 lines)

**What It Does:**
- Unified system for both theaters AND sub-HPs
- Same damage distribution logic for both
- Functions for add/remove/damage/heal/close/reopen

**Key Functions:**
- `add_theater()` - Create custom theater
- `add_subhp()` - Create fleet/army/squad sub-HP
- `apply_theater_damage()` - Damage specific theater
- `apply_subhp_damage()` - Damage specific unit
- `apply_general_damage_to_theaters()` - Unassigned → theaters
- `apply_general_damage_to_subhps()` - Unassigned → units

###  Phase 2: Data Structure Updates ✅
**Files Modified:**
- [warbot/core/data_manager.py](warbot/core/data_manager.py:62-91) - Removed stats/theater, added theaters/subhps
- [warbot/core/combat.py](warbot/core/combat.py:20-21) - Removed `_calculate_stat_advantage()`
- [warbot/core/npc_ai.py](warbot/core/npc_ai.py:246-264) - Deprecated `generate_npc_stats()`

**File Created:** [warbot/core/migration.py](warbot/core/migration.py:1) - Migration utilities

**Changes Made:**
- ❌ Removed `war["stats"]` - No more exosphere/naval/military
- ❌ Removed `war["theater"]` - No more Exosphere/Naval/Land labels
- ✅ Added `war["theaters"]` - Custom GM-created theater array
- ✅ Added `war["theater_unassigned"]` - Unassigned warbar
- ✅ Added `war["attacker_subhps"]` - Fleet/army/squad tracking
- ✅ Added `war["defender_subhps"]` - Fleet/army/squad tracking
- ✅ Added `war["attacker_unassigned_hp"]` - Unassigned HP pool
- ✅ Added `war["defender_unassigned_hp"]` - Unassigned HP pool

---

## ⏳ Remaining Phases

### Phase 3: Create New Commands (Next)
Need to create:
- `/war theater` - Manage custom theaters
- `/war subhp` - Manage sub-healthbars

### Phase 4: Consolidate ALL War Commands
Transform all war commands to action-based pattern:
- `/war manage` - Create, End, Status
- `/war battle` - Resolve, Next
- `/war roster` - Add, Remove, List
- `/war settings` - Mode, Name, Channel
- etc.

### Phase 5: Consolidate Intrigue/Superunit
Same action-based pattern for intrigue and superunit commands

### Phase 6: Testing & Polish
- Test all new systems
- Update help docs
- Final polish

---

## 🔄 Current System State

### Combat System (After Phase 2):
```python
# Before:
Roll = d20 + stat_advantage + modifiers
# Attacker 50 military vs Defender 30 military = +2 advantage

# After:
Roll = d20 + modifiers
# No stat advantages - pure tactical choices!
# Modifiers come from: actions, terrain, preparation, momentum
```

### NPC System (Still Works!):
```python
# NPCs still work - just without stats!
# They choose actions based on:
- Personality (Aggressive, Defensive, etc.)
- Archetype preferences (Eldritch Hive likes super_unit)
- Learning from past battles
- Current war state

# Example:
/war npc action:Setup side:Defender archetype:"Eldritch Hive" personality:Berserker
→ No stats generated
→ NPC makes tactical choices based on Eldritch + Berserker behavior
→ Combat still works with modifiers!
```

---

## 📊 New Data Structure Example

```json
{
  "id": 42,
  "name": "Demon Invasion",
  "attacker": "Demons",
  "defender": "Coalition",
  "warbar": 140,
  "max_value": 400,

  "theaters": [
    {
      "id": 1,
      "name": "Pennsylvania",
      "max_value": 40,
      "current_value": 20,
      "status": "active",
      "side_captured": null
    },
    {
      "id": 2,
      "name": "Gulf/Bahamas",
      "max_value": 50,
      "current_value": -10,
      "status": "active",
      "side_captured": null
    },
    {
      "id": 3,
      "name": "Georgia",
      "max_value": 50,
      "current_value": 0,
      "status": "active",
      "side_captured": null
    }
  ],
  "theater_unassigned": 130,

  "attacker_subhps": [
    {
      "id": 1,
      "name": "Hellfire Legion",
      "max_hp": 150,
      "current_hp": 100,
      "status": "active"
    },
    {
      "id": 2,
      "name": "Void Reavers",
      "max_hp": 100,
      "current_hp": 0,
      "status": "neutralized"
    }
  ],
  "defender_subhps": [],

  "attacker_unassigned_hp": 50,
  "defender_unassigned_hp": 250
}
```

---

## 🔧 What's Changed for Users

### Before (Old System):
```
/war start attacker:"Demons" defender:"Coalition" theater:Land
/war set_stats war_id:1 side:Attacker exosphere:30 naval:20 military:90
/war set_theater war_id:1 theater:Naval
```

### After (New System):
```
/war manage action:Create attacker:"Demons" defender:"Coalition"
/war theater war_id:1 action:Add name:"Pennsylvania" max_value:40
/war theater war_id:1 action:Add name:"Gulf" max_value:50
/war subhp war_id:1 action:Add side:Attacker name:"1st Fleet" max_hp:150
```

---

## ⚠️ Known Issues / TODOs

1. **Old consolidated commands need updates:**
   - `/war update` still tries to generate stats from archetypes → needs removal
   - `/war config` has Stats/Theater modes → needs removal

2. **War commands need full consolidation:**
   - Still have scattered commands like `/war start`, `/war end`, etc.
   - Need to consolidate to action-based pattern

3. **Help documentation needs updates:**
   - Remove stat/theater references
   - Add theater/subhp system docs

4. **Testing needed:**
   - Migration of existing wars
   - Theater damage distribution
   - Sub-HP damage distribution
   - NPC behavior without stats

---

## 🎯 Next Steps

**Immediate:** Create `/war theater` and `/war subhp` commands
**Short-term:** Consolidate all commands to action-based
**Long-term:** Full testing and documentation

---

**This is a MASSIVE system overhaul. Testing incrementally is recommended!**

Ready to push Phase 1-2 for server testing, or continue with Phase 3?
