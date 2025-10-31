# 🔧 CRASH FIX #2 - War Cog Conflicts

**Date:** 2025-10-31
**Error:** `discord.errors.ClientException: Cog named 'war' already loaded`

---

## 🐛 Problem

After deleting old intrigue/superunit command files, the bot now had **3 war command files** all registering as `name="war"`:

1. `war_commands_consolidated.py` - OLD file with `/war update`, `/war config`, `/war modifier`, `/war npc`, `/war roster`
2. `war_consolidated_v2.py` - NEW file with `/war manage`, `/war battle`, `/war roster`, `/war settings`
3. `war_theater_subhp.py` - NEW file with `/war theater`, `/war subhp`

**The conflict:** Both `war_commands_consolidated.py` and `war_consolidated_v2.py` have a `/war roster` command!

Discord.py allows multiple GroupCogs with the same group name (`name="war"`) ONLY if they don't have overlapping command names. The duplicate `/war roster` command caused the crash.

---

## ✅ Solution

**Temporary Fix:** Renamed `war_commands_consolidated.py` → `_old_war_commands_consolidated.py` to disable it.

```bash
mv warbot/commands/war_commands_consolidated.py → warbot/commands/_old_war_commands_consolidated.py
```

---

## ⚠️ Side Effects

By disabling `war_commands_consolidated.py`, we lost these commands:
- ❌ `/war update` - Not needed (replaced by `/war settings`)
- ❌ `/war config` - Not needed (was for stats system which is removed)
- ❌ `/war roster` - Not needed (replaced by new action-based `/war roster`)
- ⚠️ `/war modifier` - **NEEDED! Missing now**
- ⚠️ `/war npc` - **NEEDED! Missing now**

---

## 📁 Active War Command Files (After Fix)

### ✅ LOADED:
1. `war_consolidated_v2.py` - `/war manage`, `/war battle`, `/war roster`, `/war settings`
2. `war_theater_subhp.py` - `/war theater`, `/war subhp`

### ❌ DISABLED:
1. `_old_war_commands_consolidated.py` - `/war modifier`, `/war npc` (needed), plus old commands

---

## 🔧 TODO: Missing Commands

Need to add these commands back into one of the active files:

### `/war modifier` command:
- **Action:** Add, Remove, List
- **Purpose:** Manage combat modifiers (permanent or temporary)
- **Usage:** `/war modifier war_id:1 action:Add side:Attacker name:"Terrain Advantage" value:2`

### `/war npc` command:
- **Action:** Setup, Auto-Resolve, Escalate
- **Purpose:** Configure NPC-controlled sides with AI behavior
- **Usage:** `/war npc war_id:1 action:Setup side:Defender archetype:"Eldritch Hive" personality:Aggressive`

**Recommendation:** Extract `/war modifier` and `/war npc` from `_old_war_commands_consolidated.py` and add them to `war_consolidated_v2.py`

---

## 🧪 Testing

**Expected Result:** Bot should now start successfully without cog name conflicts.

**Known Limitation:** `/war modifier` and `/war npc` commands are temporarily unavailable.

---

**Status:** ✅ PARTIALLY FIXED - Bot should start, but missing 2 commands
**Next Step:** Add `/war modifier` and `/war npc` to new consolidated file
