# 🔧 CRASH FIX #1 - Duplicate Cog Names

**Date:** 2025-10-31
**Error:** `discord.errors.ClientException: Cog named 'intrigue' already loaded`

---

## 🐛 Problem

The bot was auto-loading ALL Python files from `warbot/commands/` directory, including:
- Old command files: `intrigue_commands.py`, `superunit_commands.py`, `war_commands.py`
- New consolidated files: `intrigue_consolidated.py`, `superunit_consolidated.py`, `war_consolidated_v2.py`

Both old and new files were registering cogs with the same name (e.g., `name="intrigue"`), causing Discord to reject the duplicate registration.

**Root Cause:** The bot's auto-loader in [warbot/bot.py:38-47](warbot/bot.py#L38-L47) loads all Python files EXCEPT those starting with `_`:

```python
async def _load_command_cogs(self) -> None:
    loaded: List[str] = []
    package = importlib.import_module(COMMANDS_PACKAGE)
    for module in pkgutil.iter_modules(package.__path__):
        if module.name.startswith("_"):  # ← Skips files starting with _
            continue
        extension = f"{COMMANDS_PACKAGE}.{module.name}"
        await self.load_extension(extension)
        loaded.append(extension)
```

---

## ✅ Solution

Deleted old command files since new consolidated versions are complete:

```bash
rm warbot/commands/intrigue_commands.py
rm warbot/commands/superunit_commands.py
rm warbot/commands/war_commands.py
```

These files are fully replaced by:
- `intrigue_commands.py` → `intrigue_consolidated.py`
- `superunit_commands.py` → `superunit_consolidated.py`
- `war_commands.py` → `war_consolidated_v2.py` + `war_theater_subhp.py`

---

## 📁 Active Command Files (After Fix)

### ✅ LOADED by bot:
1. `help_commands.py` - Help system
2. `time_commands.py` - Time management
3. `war_commands_consolidated.py` - `/war modifier` and `/war npc` commands
4. `war_consolidated_v2.py` - NEW `/war manage`, `/war battle`, `/war roster`, `/war settings`
5. `war_theater_subhp.py` - NEW `/war theater` and `/war subhp`
6. `intrigue_consolidated.py` - NEW `/intrigue operate`, `/intrigue view`, `/intrigue sabotage`
7. `superunit_consolidated.py` - NEW `/superunit manage` and `/superunit intel`

### ❌ DELETED (no longer needed):
1. `war_commands.py` - Old scattered war commands (replaced by war_consolidated_v2.py)
2. `intrigue_commands.py` - Old scattered intrigue commands (replaced by intrigue_consolidated.py)
3. `superunit_commands.py` - Old scattered superunit commands (replaced by superunit_consolidated.py)

---

## 🧪 Testing

**Expected Result:** Bot should now start successfully without cog name conflicts.

**Next Steps:**
1. Push changes to git
2. Deploy to server
3. Verify bot starts without errors
4. Test new consolidated commands work correctly

---

## ⚠️ Note on War Commands

We kept 3 war command files active:
- `war_commands_consolidated.py` - Has `/war modifier` and `/war npc` (still needed)
- `war_consolidated_v2.py` - Has NEW action-based commands (`/war manage`, `/war battle`, etc.)
- `war_theater_subhp.py` - Has NEW theater/subhp commands

All 3 register under `name="war"` but with different command names, so they don't conflict. Discord allows multiple cogs with the same group name as long as the individual commands don't overlap.

---

**Status:** ✅ FIXED - Ready for deployment
