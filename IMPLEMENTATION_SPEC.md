# Command Consolidation - Detailed Implementation Specification

**Status:** Ready for review and approval
**Backup:** `backups/backup_consolidation_2025-10-28_04-40-24/`
**Breaking Changes:** YES - old commands will be removed immediately

---

## Summary of Changes

### New Features Added
✅ **20 Total Archetypes** (up from 7):
- Added: Void Fleet, Orbital Supremacy (space-focused)
- Added: Grand Armada, Thalassocracy, Leviathan Corps (naval-focused)
- Added: Void Cult, Eldritch Hive, Nightmare Legion, Old Ones, Infernal Legions (eldritch/aberrant)
- Added: Psionic Covenant, Thought Collective, Psychic Ascendancy (psionic)

✅ **Complete Narrative Templates**: All 20 archetypes have unique flavor text for attack/defend/super unit actions

✅ **`/help` Command System**: 7 comprehensive help commands for self-service learning

✅ **Improved `/war action`**: Better parameter descriptions explaining narrative links and rolling

###Commands To Be Consolidated

**Current:** 40 total commands
**After:** 34 commands (-15%)
- `/war`: 21 → 11 commands (-48%)
- `/intrigue`: 8 → 7 commands
- `/time`: 6 → 4 commands
- `/help`: 0 → 7 commands (NEW!)

---

## Detailed Command Specifications

### `/war update` - ALL-IN-ONE WAR EDITING

**Purpose:** Consolidate roster management, settings, and basic info editing into ONE command

**Replaces:**
- `/war roster_add`
- `/war roster_remove`
- `/war roster_list` → becomes `/war roster list` (read-only)
- `/war mention_mode`

**Command Structure:**
```python
@app_commands.command(
    name="update",
    description="Update war settings, roster, name, channel, or mention mode (GM only)"
)
@app_commands.guild_only()
async def war_update(
    self,
    interaction: discord.Interaction,
    war_id: int,  # REQUIRED - autocomplete from active wars

    # === ROSTER MANAGEMENT ===
    roster_action: Optional[Literal["Add Player", "Remove Player", "None"]] = "None",
    roster_side: Optional[Literal["Attacker", "Defender"]] = None,  # Required if roster_action != None
    roster_player: Optional[discord.Member] = None,  # Required if Add Player
    roster_participant_id: Optional[int] = None,  # Required if Remove Player (autocomplete from roster)
    roster_archetype: Optional[str] = None,  # NEW! Optional archetype for player stat generation
    roster_tech_level: Optional[str] = None,  # NEW! Optional tech level for player stats

    # === BASIC INFO ===
    name: Optional[str] = None,
    attacker: Optional[str] = None,
    defender: Optional[str] = None,
    channel: Optional[discord.TextChannel] = None,

    # === SETTINGS ===
    mention_mode: Optional[Literal["Team Roles", "Individual Players"]] = None,

) -> None:
```

**Behavior:**
- Only updates fields that are provided (None = skip)
- **Roster Management:**
  - If `roster_action="Add Player"`:
    - Requires: `roster_side`, `roster_player`
    - Optional: `roster_archetype`, `roster_tech_level` (NEW!)
    - If archetype provided: Auto-generates stats using NPC system
    - If no archetype: Player stats remain as-is (manual `/war config` needed)
  - If `roster_action="Remove Player"`:
    - Requires: `roster_side`, `roster_participant_id`
    - Autocomplete shows participant names from that side's roster
- **Mention Mode:**
  - If changed, creates/removes Discord roles as needed
  - Warns if role creation fails (permissions)

**Response:**
```
✅ War #1 Updated

📋 Changes Made:
• Added @PlayerName to Attacker side
  📊 Generated stats from Elite archetype (Modern tech):
     Exosphere: 36 (30 × 1.2)
     Naval: 24 (20 × 1.2)
     Military: 60 (50 × 1.2)
• Mention mode set to Individual Players

Use `/war status war_id:1` to view full war details.
```

---

### `/war config` - STATS, ARCHETYPE, THEATER, MODE CONFIGURATION

**Purpose:** All war configuration in one place with clear type selection

**Replaces:**
- `/war set_stats`
- `/war set_theater`
- `/war set_mode`
- Part of `/war set_npc` (archetype application)

**Command Structure:**
```python
@app_commands.command(
    name="config",
    description="Configure war stats, archetype, theater, or mode (GM only)"
)
@app_commands.guild_only()
async def war_config(
    self,
    interaction: discord.Interaction,
    war_id: int,  # REQUIRED - autocomplete
    config_type: Literal["Stats", "Archetype", "Theater", "Mode"],  # REQUIRED - determines which params are used

    # === COMMON ===
    side: Optional[Literal["Attacker", "Defender"]] = None,  # Required for Stats/Archetype

    # === IF config_type="Stats" ===
    exosphere: Optional[int] = None,
    naval: Optional[int] = None,
    military: Optional[int] = None,

    # === IF config_type="Archetype" ===
    archetype: Optional[str] = None,  # Choices from all 20 archetypes
    tech_level: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
    personality: Optional[Literal["Aggressive", "Defensive", "Adaptive", "Balanced", "Berserker"]] = None,  # Only for NPCs

    # === IF config_type="Theater" ===
    theater: Optional[Literal["Exosphere", "Naval", "Land", "Multi-Theater"]] = None,

    # === IF config_type="Mode" ===
    mode: Optional[Literal["Player-Driven", "GM-Driven", "NPC Auto-Resolve"]] = None,
    cooldown_hours: Optional[int] = 12,  # Only for Player-Driven mode

) -> None:
```

**Behavior:**
- **Stats Mode**: Manually set stats (traditional method)
- **Archetype Mode**:
  - **NEW!** Works for both NPCs AND players
  - Auto-generates stats using archetype + tech level
  - If personality provided: Marks as NPC-controlled
  - If no personality: Treats as player using that archetype's doctrine
- **Theater Mode**:
  - Sets theater
  - Explains theater effects: "Land theater prioritizes Military stat (50% weight vs 25% for others)"
- **Mode Mode**:
  - Changes resolution mode
  - Validates based on war setup (e.g., can't use NPC Auto-Resolve unless both sides are NPCs)

**Response Examples:**

*Stats Mode:*
```
✅ Stats Updated for War #1 - Attacker Side

Exosphere: 60
Naval: 50
Military: 70

Total Power: 180
```

*Archetype Mode (Player):*
```
✅ Archetype Applied: Attacker Side

📊 Void Fleet (Advanced Tech)
Auto-generated stats:
• Exosphere: 72 (60 × 1.2)
• Naval: 24 (20 × 1.2)
• Military: 24 (20 × 1.2)

Total Power: 120

This is a PLAYER side using Void Fleet doctrine.
Use `/war config config_type:Mode` if you want NPC control.
```

*Archetype Mode (NPC):*
```
✅ NPC Configured: Defender Side

🤖 Insurgent/Rebel Force (Legacy Tech, Aggressive)
Auto-generated stats:
• Exosphere: 3.5 (5 × 0.7)
• Naval: 3.5 (5 × 0.7)
• Military: 63 (90 × 0.7)

Total Power: 70
Aggression: 0.9 (Insurgent 0.6 + Aggressive +0.3)

This side is NPC-controlled and will auto-respond to player actions.
```

*Theater Mode:*
```
✅ Theater Set: Land

⚔️ Theater Effects:
• Military stat weighted 50% (primary)
• Exosphere/Naval weighted 25% each (supporting)

This theater favors ground-focused forces.
```

---

### `/war modifier` - MODIFIER MANAGEMENT

**Purpose:** Consolidate add/remove modifiers with list capability

**Replaces:**
- `/war add_modifier`
- `/war remove_modifier`

**Command Structure:**
```python
@app_commands.command(
    name="modifier",
    description="Manage combat modifiers: add, remove, or list (GM only)"
)
@app_commands.guild_only()
async def war_modifier(
    self,
    interaction: discord.Interaction,
    war_id: int,  # REQUIRED - autocomplete
    action: Literal["Add", "Remove", "List"],  # REQUIRED

    # === IF action="Add" ===
    side: Optional[Literal["Attacker", "Defender"]] = None,  # Required for Add/Remove
    name: Optional[str] = None,  # Required for Add
    value: Optional[int] = None,  # Required for Add
    duration: Optional[Literal["Permanent", "Next Resolution", "2 Turns", "3 Turns", "5 Turns"]] = "Permanent",

    # === IF action="Remove" ===
    modifier_id: Optional[int] = None,  # Required for Remove (autocomplete from modifiers)

) -> None:
```

**Behavior:**
- **Add**: Creates new modifier
- **Remove**: Deletes by ID (autocomplete shows active modifiers)
- **List**: Shows all modifiers for both sides

**Response Examples:**

*Add:*
```
✅ Modifier Added: Attacker Side

**Fortified Position** (+3)
Duration: Permanent

Current Attacker Modifiers:
• Fortified Position: +3 (Permanent)
• Air Superiority: +2 (3 turns remaining)

Total Modifier: +5
```

*List:*
```
📋 Modifiers for War #1

**Attacker:**
• ID 1: Fortified Position (+3, Permanent)
• ID 2: Air Superiority (+2, 3 turns)
Total: +5

**Defender:**
• ID 3: Damaged Infrastructure (-2, Permanent)
• ID 4: Low Morale (-1, 2 turns)
Total: -3
```

---

### `/war npc` - NPC MANAGEMENT

**Purpose:** All NPC-related commands in one place

**Replaces:**
- `/war set_npc`
- `/war set_auto_resolve`
- `/war stop_auto`
- `/war escalate`

**Command Structure:**
```python
@app_commands.command(
    name="npc",
    description="Manage NPC sides: setup, auto-resolution, or escalation (GM only)"
)
@app_commands.guild_only()
async def war_npc(
    self,
    interaction: discord.Interaction,
    war_id: int,  # REQUIRED - autocomplete
    action: Literal["Setup", "Auto-Resolve", "Escalate"],  # REQUIRED

    # === IF action="Setup" ===
    side: Optional[Literal["Attacker", "Defender"]] = None,  # Required for Setup
    archetype: Optional[str] = None,  # Required for Setup (20 choices)
    tech_level: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,  # Required for Setup
    personality: Optional[Literal["Aggressive", "Defensive", "Adaptive", "Balanced", "Berserker"]] = None,  # Required for Setup

    # === IF action="Auto-Resolve" ===
    enabled: Optional[bool] = None,  # Required for Auto-Resolve
    interval_hours: Optional[int] = 12,
    max_turns: Optional[int] = 50,

    # === IF action="Escalate" ===
    escalation_type: Optional[Literal["To PvE", "To PvP"]] = None,  # Required for Escalate
    new_mode: Optional[Literal["Player-Driven", "GM-Driven"]] = None,  # Required for Escalate

) -> None:
```

**Behavior:**
- **Setup**: Configures one side as NPC (same as old `/war set_npc`)
  - If both sides become NPCs: Prompts about auto-resolution
- **Auto-Resolve**:
  - `enabled=True`: Starts NPC vs NPC auto-resolution
  - `enabled=False`: Stops auto-resolution
  - Validates both sides are NPCs before enabling
- **Escalate**:
  - `To PvE`: Disables NPC for one side, stops auto-resolve
  - `To PvP`: Disables NPC for both sides, stops auto-resolve
  - Changes mode to specified value

**Response Examples:**

*Setup:*
```
✅ NPC Configured: Defender Side

🤖 Eldritch Hive (Cutting Edge Tech, Berserker)

📊 Generated Stats:
• Exosphere: 42 (30 × 1.4)
• Naval: 28 (20 × 1.4)
• Military: 70 (50 × 1.4)

Total Power: 140
Aggression: 1.35 (Eldritch Hive 0.85 + Berserker +0.5)

**Archetype Traits:**
Biomechanical swarm intelligence with incomprehensible tactics

⚠️ Both Sides Now NPC-Controlled!
Use `/war npc action:Auto-Resolve war_id:1 enabled:True` to enable autonomous war resolution.
```

*Auto-Resolve Enable:*
```
✅ NPC Auto-Resolution Enabled

⚙️ Configuration:
• Interval: Every 12 hours
• Max Turns: 50 (defender wins if reached)
• Critical HP: GM pinged when either side near death

🤖 War will now resolve autonomously in the background!
Next resolution: <t:1730123456:R> (in ~12 hours)
```

*Escalate:*
```
✅ War Escalated to PvE

📈 Changes:
• Defender NPC disabled (now player-controlled)
• Auto-resolution stopped
• Mode changed to Player-Driven

**Next Steps:**
1. Use `/war update roster_action:Add war_id:1` to add players to Defender side
2. Players use `/war action` to submit combat actions
3. Former NPC side now requires player input
```

---

### `/war create` - SMART WAR CREATION WIZARD

**Purpose:** One-shot war creation with context-aware prompts based on war type

**Updates:** Adds `war_type` parameter that changes available options

**Command Structure:**
```python
@app_commands.command(
    name="create",
    description="Create a new war with smart setup wizard (GM only)"
)
@app_commands.guild_only()
async def war_create(
    self,
    interaction: discord.Interaction,
    attacker: str,  # REQUIRED
    defender: str,  # REQUIRED
    war_type: Literal["PvP", "PvE", "EvE"],  # NEW! REQUIRED - determines setup flow
    theater: Literal["Exosphere", "Naval", "Land", "Multi-Theater"],  # REQUIRED
    channel: discord.TextChannel,  # REQUIRED

    # === IF war_type="PvP" ===
    attacker_archetype: Optional[str] = None,  # Optional - for stat generation
    attacker_tech: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
    defender_archetype: Optional[str] = None,
    defender_tech: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,

    # === IF war_type="PvE" ===
    npc_side: Optional[Literal["Attacker", "Defender"]] = None,  # Required for PvE
    npc_archetype: Optional[str] = None,  # Required for PvE
    npc_tech: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
    npc_personality: Optional[Literal["Aggressive", "Defensive", "Adaptive", "Balanced", "Berserker"]] = None,
    player_archetype: Optional[str] = None,  # Optional - for player stat generation
    player_tech: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,

    # === IF war_type="EvE" ===
    attacker_npc_archetype: Optional[str] = None,  # Required for EvE
    attacker_npc_tech: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
    attacker_npc_personality: Optional[Literal["Aggressive", "Defensive", "Adaptive", "Balanced", "Berserker"]] = None,
    defender_npc_archetype: Optional[str] = None,  # Required for EvE
    defender_npc_tech: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
    defender_npc_personality: Optional[Literal["Aggressive", "Defensive", "Adaptive", "Balanced", "Berserker"]] = None,
    auto_resolve: Optional[bool] = True,  # For EvE - auto-enable auto-resolution?
    auto_interval: Optional[int] = 12,

) -> None:
```

**Behavior:**
- **PvP Mode:**
  - Creates war with both sides as players
  - If archetypes provided: Auto-generates stats for both sides
  - Sets mode to GM-Driven by default
  - Prompts to add players via `/war update`

- **PvE Mode:**
  - Creates war with one NPC side
  - Generates NPC stats from archetype/tech/personality
  - If player_archetype provided: Generates player stats too
  - Sets mode to Player-Driven automatically
  - Prompts to add players via `/war update`

- **EvE Mode:**
  - Creates war with both sides as NPCs
  - Generates stats for both NPCs
  - If auto_resolve=True: Enables auto-resolution immediately
  - Sets mode to NPC Auto-Resolve
  - Posts initial war state to channel

**Response Examples:**

*PvP War:*
```
✅ War Created: War #1

**Attacker:** Terran Federation
**Defender:** Zerg Swarm
**Theater:** Land
**Type:** PvP (Player vs Player)

📊 Generated Stats:
**Attacker** (NATO Doctrine, Modern Tech):
• Exosphere: 30, Naval: 30, Military: 40 (Total: 100)

**Defender** (Swarm Doctrine, Modern Tech):
• Exosphere: 40, Naval: 20, Military: 40 (Total: 100)

**Next Steps:**
1. Add players: `/war update war_id:1 roster_action:Add ...`
2. Set mode: `/war config war_id:1 config_type:Mode mode:Player-Driven` (or GM-Driven)
3. Start fighting!
```

*EvE War with Auto-Resolve:*
```
✅ EvE War Created and Auto-Resolution Enabled

**War #1:** Imperial Fleet vs Rebel Insurgency
**Theater:** Multi-Theater
**Type:** EvE (Environment vs Environment - Fully Autonomous)

🤖 Attacker NPC:
• Archetype: Void Fleet (Cutting Edge, Aggressive)
• Stats: Exosphere 84, Naval 28, Military 28 (Total: 140)

🤖 Defender NPC:
• Archetype: Insurgent (Legacy, Berserker)
• Stats: Exosphere 3.5, Naval 3.5, Military 63 (Total: 70)

⚙️ Auto-Resolution:
• Enabled: Yes
• Interval: Every 12 hours
• Max Turns: 50
• Next Resolution: <t:1730123456:R>

This war will run autonomously in the background. Check #{channel.name} for updates!
```

---

### Commands To Be REMOVED

The following commands will be **deleted entirely**:

```
/war roster_add
/war roster_remove
/war mention_mode
/war set_stats
/war set_theater
/war set_mode
/war set_npc
/war add_modifier
/war remove_modifier
/war set_auto_resolve
/war stop_auto
/war escalate
```

**Replacement mapping:**
- `roster_add` → `/war update roster_action:Add`
- `roster_remove` → `/war update roster_action:Remove`
- `mention_mode` → `/war update mention_mode:...`
- `set_stats` → `/war config config_type:Stats`
- `set_theater` → `/war config config_type:Theater`
- `set_mode` → `/war config config_type:Mode`
- `set_npc` → `/war npc action:Setup` OR `/war config config_type:Archetype` (for players!)
- `add_modifier` → `/war modifier action:Add`
- `remove_modifier` → `/war modifier action:Remove`
- `set_auto_resolve` → `/war npc action:Auto-Resolve enabled:True`
- `stop_auto` → `/war npc action:Auto-Resolve enabled:False`
- `escalate` → `/war npc action:Escalate`

---

### `/war roster list` - READ-ONLY ROSTER VIEWING

**Purpose:** View rosters without modification capability

**Command Structure:**
```python
@app_commands.command(
    name="list",
    description="View war rosters (players can use this)"
)
@app_commands.guild_only()
async def war_roster_list(
    self,
    interaction: discord.Interaction,
    war_id: int,  # REQUIRED - autocomplete
) -> None:
```

**Note:** This is a NEW top-level subcommand under `/war roster` group, not under `/war` directly

---

## Final Command Structure

### `/war` - 11 subcommands (down from 21)
```
PLAYER COMMANDS (3):
/war action        - Submit combat action
/war status        - View war details
/war list          - See active wars

GM COMMANDS (7):
/war create        - Smart war creation wizard
/war update        - Edit war (roster, settings, info)
/war config        - Configure stats/archetype/theater/mode
/war modifier      - Manage modifiers (add/remove/list)
/war npc           - NPC management (setup/auto-resolve/escalate)
/war resolve       - Execute GM-driven combat
/war end           - Conclude war

INFO COMMANDS (1):
/war roster list   - View rosters
```

---

## Implementation Checklist

### Phase 1: New Command Implementation
- [ ] Implement `/war update` with roster management + player archetypes
- [ ] Implement `/war config` with all 4 config types
- [ ] Implement `/war modifier` with add/remove/list
- [ ] Implement `/war npc` with setup/auto-resolve/escalate
- [ ] Update `/war create` with war_type wizard
- [ ] Create `/war roster list` as separate read-only command

### Phase 2: Removal
- [ ] Delete all 12 old commands listed above
- [ ] Remove their autocomplete methods
- [ ] Remove from cog registration

### Phase 3: Testing
- [ ] Test PvP war creation with player archetypes
- [ ] Test PvE war creation
- [ ] Test EvE war creation with auto-resolve
- [ ] Test roster add with archetype (player stat generation)
- [ ] Test all 4 config types
- [ ] Test modifier add/remove/list
- [ ] Test NPC setup/escalate
- [ ] Test auto-resolve enable/disable

### Phase 4: Documentation
- [ ] Update COMMAND_REFERENCE.md
- [ ] Update PVE_SYSTEM_GUIDE.md with player archetypes
- [ ] Update WAR_2.0_UPDATE_SUMMARY.md
- [ ] Create migration guide for users

---

## Breaking Changes Warning

**This will break existing workflows!** Old commands will NOT work after implementation.

**Migration period:** NONE (Option B - immediate removal)

**User:** You (Bravo) - the only user, so acceptable

**Rollback:** Backup available at `backups/backup_consolidation_2025-10-28_04-40-24/`

---

## Approval Checklist

Before I proceed with implementation, please confirm:

- [ ] **Command structure approved**: You're okay with the parameters and behavior described above
- [ ] **Player archetypes approved**: Players can be assigned archetypes for auto-stat generation
- [ ] **Breaking changes approved**: Old commands will be deleted immediately
- [ ] **War creation wizard approved**: PvP/PvE/EvE types with context-aware parameters
- [ ] **Ready to proceed**: I should start implementing these changes

**Reply "APPROVED" to begin implementation, or provide feedback for changes.**

---

**Total Estimated Implementation Time:** 3-4 hours
**Risk Level:** HIGH (major refactoring, breaking changes)
**Backup Status:** ✅ Created
**Archetype Count:** ✅ 20 total with full narrative support
**Help System:** ✅ Already implemented
