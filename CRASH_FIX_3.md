# 🔧 CRASH FIX #3 - War Cog Name Conflict (Still)

**Date:** 2025-10-31
**Error:** `discord.errors.ClientException: Cog named 'war' already loaded` (from war_theater_subhp.py)

---

## 🐛 Problem

Even after disabling `war_commands_consolidated.py`, we still had TWO war command files:
1. `war_consolidated_v2.py` - Registers as `name="war"`
2. `war_theater_subhp.py` - ALSO registers as `name="war"`

**Root Cause:** Discord.py does NOT allow multiple GroupCogs with the same `name` parameter, even if their command names don't overlap. Each GroupCog must have a unique name.

---

## ✅ Solution (Temporary)

Renamed `war_theater_subhp.py` → `_war_theater_subhp.py` to disable it temporarily.

```bash
mv warbot/commands/war_theater_subhp.py → warbot/commands/_war_theater_subhp.py
```

**This temporarily removes these commands:**
- ❌ `/war theater` - Add, Remove, Close, Reopen, Rename, List theaters
- ❌ `/war subhp` - Add, Remove, Damage, Heal, Rename, List sub-HPs

---

## 🔧 TODO: Permanent Solution

Need to **merge** `_war_theater_subhp.py` into `war_consolidated_v2.py` so all war commands are in ONE file.

### Commands to merge:
1. `/war theater` command (with all 6 actions)
2. `/war subhp` command (with all 6 actions)
3. Helper functions: `_render_mini_bar()`, `_render_hp_bar()`
4. Imports from `subbar_manager` module

### Steps:
1. Add imports from `subbar_manager` to `war_consolidated_v2.py`
2. Copy `/war theater` command method
3. Copy `/war subhp` command method
4. Copy helper functions
5. Test bot starts successfully
6. Delete `_war_theater_subhp.py`

---

## 📁 Active Command Files (After Fix)

### ✅ LOADED:
1. `war_consolidated_v2.py` - `/war manage`, `/war battle`, `/war roster`, `/war settings`
2. `intrigue_consolidated.py` - All intrigue commands
3. `superunit_consolidated.py` - All superunit commands

### ❌ DISABLED (need merging):
1. `_war_theater_subhp.py` - `/war theater`, `/war subhp` (need to merge into v2)
2. `_old_war_commands_consolidated.py` - `/war modifier`, `/war npc` (need to extract)

---

## ⚠️ Missing Commands

By disabling files, we're now missing:
- `/war theater` - Theater management
- `/war subhp` - Sub-HP management
- `/war modifier` - Combat modifiers
- `/war npc` - NPC AI configuration

**All these commands exist in the disabled files and need to be merged into `war_consolidated_v2.py`.**

---

## 🧪 Testing

**Expected Result:** Bot should now start successfully without cog conflicts.

**Known Limitation:** Missing `/war theater`, `/war subhp`, `/war modifier`, `/war npc` commands.

---

**Status:** ✅ TEMPORARY FIX - Bot should start, but commands need merging
**Next Step:** Merge all war commands into single consolidated file
