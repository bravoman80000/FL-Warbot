# 🚀 OPERATION GREENLIGHT 2.0 - Ready for Push

**Date:** 2025-10-30
**Status:** Phases 1-3 Complete - Core System Implemented
**Ready For:** Server Testing + Bug Sweep

---

## ✅ What's Been Completed

### Phase 1-2: Core System Overhaul
**Files Created:**
- ✅ [warbot/core/subbar_manager.py](warbot/core/subbar_manager.py:1) - 550 lines
- ✅ [warbot/core/migration.py](warbot/core/migration.py:1) - Migration utilities

**Files Modified:**
- ✅ [warbot/core/data_manager.py](warbot/core/data_manager.py:62-91) - Removed stats/theater, added new systems
- ✅ [warbot/core/combat.py](warbot/core/combat.py:20-21) - Removed stat advantages
- ✅ [warbot/core/npc_ai.py](warbot/core/npc_ai.py:246-264) - Deprecated stat generation

**What Changed:**
- ❌ **REMOVED:** `war["stats"]` - exosphere/naval/military system
- ❌ **REMOVED:** `war["theater"]` - fixed Exosphere/Naval/Land labels
- ❌ **REMOVED:** Stat-based combat advantages
- ✅ **ADDED:** `war["theaters"]` - custom GM-created theater array
- ✅ **ADDED:** `war["attacker_subhps"]` / `war["defender_subhps"]` - unit tracking
- ✅ **ADDED:** Unified damage distribution system

### Phase 3: New Commands
**File Created:**
- ✅ [warbot/commands/war_theater_subhp.py](warbot/commands/war_theater_subhp.py:1) - 670 lines

**New Commands:**
```
/war theater <action>
  Actions: Add, Remove, Close, Reopen, Rename, List

/war subhp <action>
  Actions: Add, Remove, Damage, Heal, Rename, List
```

---

## 📊 New System At A Glance

### Custom Theaters (Multi-Front Tracking):
```
/war theater war_id:1 action:Add name:"Pennsylvania" max_value:40
/war theater war_id:1 action:Add name:"Gulf Theater" max_value:50
/war theater war_id:1 action:List

📊 Display:
  🗺️ Pennsylvania: [===|--] +20/40 (Attacker advancing)
  🗺️ Gulf Theater: [--|===] -15/50 (Defender pushing)
  📊 Unassigned: +135 (general warbar)
```

### Sub-Healthbars (Unit Tracking):
```
/war subhp war_id:1 action:Add side:Attacker name:"1st Fleet" max_hp:150
/war subhp war_id:1 action:Damage side:Attacker subhp_id:1 amount:50
/war subhp war_id:1 action:List

📊 Display:
  ⚡ 1st Fleet: [██████----] 100/150 HP
  ⚡ 2nd Fleet: [██████████] 150/150 HP
  ☠️ 3rd Fleet: [----------] NEUTRALIZED
```

### Combat Without Stats:
```
Before: d20 + stat_advantage + modifiers
After:  d20 + modifiers

Modifiers from:
- Defense Stance: +2
- Prepare Attack: +1
- Sabotage (enemy): -1
- Tactical Momentum: +1 to +3
- GM Custom Modifiers: variable
```

---

## ⚠️ Breaking Changes

### Data Structure:
```json
// OLD (removed):
"stats": {"attacker": {"exosphere": 50, "naval": 30, "military": 70}},
"theater": "land"

// NEW:
"theaters": [
  {"id": 1, "name": "Pennsylvania", "max_value": 40, "current_value": 20}
],
"attacker_subhps": [
  {"id": 1, "name": "1st Fleet", "max_hp": 150, "current_hp": 100}
]
```

### Commands Still Need Updating:
These old commands still exist (will error or behave oddly):
- `/war start` - Has removed `theater` parameter (needs update)
- `/war set_stats` - **DOESN'T WORK** (stats removed)
- `/war set_theater` - **DOESN'T WORK** (theater labels removed)
- `/war update` (consolidated) - Still tries to generate stats from archetypes
- `/war config` (consolidated) - Has Stats/Theater modes that don't work

### Migration:
- Existing wars will auto-migrate (stats/theater removed)
- Custom theaters start empty (GMs must add them)
- Sub-HPs start empty (GMs must add them)

---

## 🎯 What Still Needs Doing

### Phase 4: Command Consolidation (Remaining)
Transform ALL war commands to action-based:

**Current messy structure:**
```
/war start
/war end
/war status
/war resolve
/war next
/war roster_add
/war roster_remove
/war update
/war config
... etc (21 commands total)
```

**Target clean structure:**
```
/war manage <action>     - Create, End, Status
/war battle <action>     - Resolve, Next
/war roster <action>     - Add, Remove, List
/war settings <action>   - Mode, Name, Channel
/war modifier <action>   - Add, Remove, List (DONE)
/war npc <action>        - Setup, Auto-Resolve, Escalate (DONE)
/war theater <action>    - Add, Remove, Close, Reopen, List (DONE)
/war subhp <action>      - Add, Remove, Damage, Heal, List (DONE)
/war action              - ⚔️ PLAYER COMMAND (stays standalone)
```

### Phase 5: Update Consolidated Commands
- Remove Stats mode from `/war config`
- Remove Theater mode from `/war config`
- Remove archetype stat generation from `/war update`
- Keep archetype selection (for AI behavior only)

### Phase 6: Intrigue/Superunit Consolidation
Apply same action-based pattern:
```
/intrigue operation <action>
/intrigue intel <action>
/intrigue superunit <action>
```

### Phase 7: Documentation
- Update all help commands
- Remove stat/theater references
- Add theater/subhp guides

---

## 🧪 Testing Checklist (After Push)

### Theater System:
- [ ] Add custom theater
- [ ] Apply damage to specific theater
- [ ] Close theater when limit reached
- [ ] Reopen closed theater
- [ ] Verify unassigned warbar calculation

### Sub-HP System:
- [ ] Add sub-HP to attacker/defender
- [ ] Damage specific sub-HP
- [ ] Heal neutralized sub-HP
- [ ] Verify main HP updates correctly

### Combat System:
- [ ] Resolve turn without stats (modifiers only)
- [ ] NPC vs NPC war without stats
- [ ] PvE war with NPC (no stats, just behavior)
- [ ] Verify damage distribution (general vs specific)

### Migration:
- [ ] Load existing war (should auto-migrate)
- [ ] Verify no errors from removed stats/theater
- [ ] Check all wars still functional

---

## 📁 Files Modified Summary

**Created (4 files):**
1. `warbot/core/subbar_manager.py` - 550 lines
2. `warbot/core/migration.py` - ~150 lines
3. `warbot/commands/war_theater_subhp.py` - 670 lines
4. Multiple documentation files

**Modified (3 files):**
1. `warbot/core/data_manager.py` - Removed stats, added theaters/subhps
2. `warbot/core/combat.py` - Removed stat advantages
3. `warbot/core/npc_ai.py` - Deprecated stat generation

**Total Lines Changed:** ~2,000+ lines

---

## 🚀 Deployment Plan

### Option A: Push Now, Finish Command Consolidation Later
**Push:** Phases 1-3 (core systems + new commands)
**Later:** Command consolidation (Phase 4-7)

**Pros:**
- Test core systems immediately
- Incremental deployment
- Old commands still work (mostly)

**Cons:**
- Mixed old/new command structure
- Some commands broken (set_stats, set_theater)

### Option B: Finish Everything First
**Do:** Complete Phases 4-7 before pushing
**Push:** Everything at once

**Pros:**
- Clean command structure
- All commands updated
- No broken commands

**Cons:**
- Longer before testing
- Bigger risk if something breaks

---

## 💡 Recommended Next Steps

1. **Push Phases 1-3 NOW** (what we just built)
2. **Test on server:**
   - Create war
   - Add theaters
   - Add sub-HPs
   - Test combat without stats
3. **Bug sweep:** Fix any issues found
4. **Then:** Continue with command consolidation (Phases 4-7)

This way you can test the CORE SYSTEM changes (which are massive) before we restructure all the commands.

---

**Ready to push?** Let me know and I'll help you commit everything! 🎉
