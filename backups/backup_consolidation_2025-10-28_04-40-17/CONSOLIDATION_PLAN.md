# Command Consolidation Plan

## Problems Identified

1. **40 total commands** - Too cluttered, players getting lost
2. **`/war action` buried** - THE player command, but hidden among 21 war commands
3. **Roster management scattered** - `roster_add`, `roster_remove`, `roster_list` should be in `/war update`
4. **Mention mode separate** - Should be in `/war update`
5. **Multiple "set_X" commands** - `set_stats`, `set_theater`, `set_mode`, `set_npc` feel redundant
6. **Modifier management unclear** - `add_modifier` and `remove_modifier` as separate top-level commands
7. **PvE/EvE setup unintuitive** - Requires multiple commands, easy to mess up
8. **No player archetypes** - Only NPCs get archetypes, players should too
9. **Theater unclear** - Cosmetic label vs actual stat effects
10. **No `/help` system** - Players don't know how to use commands
11. **Poor parameter descriptions** - narrative_link and roll confusing

## Solutions Implemented

### ✅ 1. Created `/help` Command System
- `/help overview` - Bot overview and command groups
- `/help action` - Step-by-step tutorial for `/war action`
- `/help war` - Complete war system guide
- `/help npc` - PvE and EvE guide
- `/help intrigue` - Intrigue operations guide
- `/help superunit` - Super unit and intel guide
- `/help quick` - Quick reference card

### ✅ 2. Improved `/war action` Descriptions
- Command description now says "⚔️ THE PLAYER COMMAND" to make it prominent
- Added `@app_commands.describe()` for all parameters:
  - **narrative_link**: Explains to write RP first, then copy message link
  - **roll**: Explicitly states "YOU roll it yourself, bot does NOT roll for you"
  - **main/minor**: Shows bonuses (+2 for defend, +1 next turn, etc.)
- Command description points to `/help action` for tutorial

## Solutions To Implement

### 3. Consolidate Roster/Settings into `/war update`

**Current:**
```
/war roster_add war_id:1 side:Attacker member:@User
/war roster_remove war_id:1 side:Attacker participant:123
/war roster_list war_id:1
/war mention_mode war_id:1 mode:Individual
```

**Proposed:**
```
/war update
  war_id: 1
  [Optional parameters - only fill what you want to change]

  # Roster management
  roster_action: [Add Player | Remove Player | None]
    ↳ If "Add Player":
        - side: [Attacker | Defender]
        - player: @mention
        - archetype: [NATO | CSAT | etc.] (optional - NEW!)
        - tech_level: [Legacy | Modern | etc.] (optional - NEW!)
    ↳ If "Remove Player":
        - side: [Attacker | Defender]
        - participant: (autocomplete from roster)

  # Settings
  mention_mode: [Team Roles | Individual Players]
  resolution_mode: [Player-Driven | GM-Driven | NPC Auto-Resolve]

  # Basic info
  name: "New War Name"
  attacker: "Faction A"
  defender: "Faction B"
  theater: [Exosphere | Naval | Land | Multi-Theater]
  channel: #new-channel
```

**Benefits:**
- All war editing in one place
- Fewer commands to remember
- Player archetypes for stat generation (NEW!)

---

### 4. Create `/war config` for Stats/NPC Setup

**Current:**
```
/war set_stats war_id:1 side:Attacker exosphere:60 naval:50 military:70
/war set_theater war_id:1 theater:Land
/war set_npc war_id:1 side:Defender archetype:Insurgent tech_level:Legacy personality:Aggressive
/war set_mode war_id:1 mode:Player-Driven
```

**Proposed:**
```
/war config
  war_id: 1
  config_type: [Stats | Archetype | Theater | Mode]

  # If Stats selected
  side: [Attacker | Defender]
  exosphere: 60
  naval: 50
  military: 70

  # If Archetype selected (works for NPCs AND players!)
  side: [Attacker | Defender]
  archetype: [NATO | CSAT | Guerrilla | etc.]
  tech_level: [Legacy | Modern | Advanced | Cutting Edge]
  personality: [Aggressive | Defensive | Adaptive | Balanced | Berserker] (only for NPCs)

  # If Theater selected
  theater: [Exosphere | Naval | Land | Multi-Theater]

  # If Mode selected
  mode: [Player-Driven | GM-Driven | NPC Auto-Resolve]
  cooldown_hours: 12 (for player-driven)
```

**Benefits:**
- Logical grouping by config type
- Player archetypes supported!
- Clear distinction between manual stats vs archetype generation

---

### 5. Consolidate Modifier Management

**Current:**
```
/war add_modifier war_id:1 side:Attacker name:"Fortified" value:3 duration:Permanent
/war remove_modifier war_id:1 side:Attacker name:"Fortified"
```

**Proposed:**
```
/war modifier
  war_id: 1
  action: [Add | Remove | List]

  # If Add
  side: [Attacker | Defender]
  name: "Fortified Position"
  value: 3
  duration: [Permanent | Next Resolution | 2 Turns | 3 Turns | 5 Turns]

  # If Remove
  side: [Attacker | Defender]
  modifier_id: (autocomplete)

  # If List
  [Shows all modifiers for both sides]
```

**Benefits:**
- Grouped functionality
- Can list modifiers in same command
- Autocomplete for removal

---

### 6. Improve `/war create` with Smart Wizard

**Current:**
```
/war create attacker:"A" defender:"B"
# Then manually:
/war set_stats ... (for side A)
/war set_stats ... (for side B)
/war set_theater ...
/war set_mode ...
/war set_npc ... (if PvE)
/war roster add ... (for each player)
```

**Proposed:**
```
/war create
  attacker: "Faction A"
  defender: "Faction B"
  war_type: [PvP | PvE | EvE]  ← Determines follow-up prompts
  theater: [Exosphere | Naval | Land | Multi-Theater]
  channel: #war-channel

  # If PvP selected:
  attacker_archetype: [NATO | CSAT | etc.] (optional - uses for stat gen)
  attacker_tech: [Legacy | Modern | etc.]
  defender_archetype: [NATO | CSAT | etc.]
  defender_tech: [Legacy | Modern | etc.]

  # If PvE selected:
  npc_side: [Attacker | Defender]
  npc_archetype: [NATO | CSAT | etc.]
  npc_tech: [Legacy | Modern | etc.]
  npc_personality: [Aggressive | Defensive | etc.]
  player_archetype: [NATO | CSAT | etc.] (optional - for stat gen)
  player_tech: [Legacy | Modern | etc.]

  # If EvE selected:
  attacker_archetype: [required]
  attacker_tech: [required]
  attacker_personality: [required]
  defender_archetype: [required]
  defender_tech: [required]
  defender_personality: [required]
  auto_resolve: [Yes | No]
  interval_hours: 12 (if auto_resolve Yes)
```

**Result:** War created with ALL settings in one command instead of 5-7 follow-ups!

**Benefits:**
- One-shot war creation
- Context-aware based on war type
- Player archetypes baked in
- Prevents forgotten setup steps

---

### 7. Consolidate NPC Commands

**Current:**
```
/war set_npc ...
/war set_auto_resolve ...
/war stop_auto ...
/war escalate ...
```

**Proposed:**
```
/war npc
  war_id: 1
  action: [Setup | Auto-Resolve | Escalate]

  # If Setup
  side: [Attacker | Defender]
  archetype: [NATO | CSAT | etc.]
  tech_level: [Legacy | Modern | etc.]
  personality: [Aggressive | Defensive | etc.]

  # If Auto-Resolve
  enabled: [True | False]
  interval_hours: 12
  max_turns: 50

  # If Escalate
  escalation_type: [To PvE | To PvP]
  new_mode: [Player-Driven | GM-Driven]
```

**Benefits:**
- All NPC management in one place
- Clearer organization

---

### 8. Clarify Theater System

**Current confusion:** Theater seems cosmetic but actually affects stats

**Solution:**
- Update all documentation to explain theater effects
- When setting theater, show message:
  ```
  Theater set to LAND
  This theater prioritizes Military stat in combat calculations.
  Exosphere/Naval stats still matter for combined arms, but Military is weighted higher.
  ```

**Theater Effects:**
- **Exosphere**: Exosphere stat weighted 50%, Naval 25%, Military 25%
- **Naval**: Naval stat weighted 50%, Exosphere 25%, Military 25%
- **Land**: Military stat weighted 50%, Exosphere 25%, Naval 25%
- **Multi-Theater**: All stats weighted equally (33/33/33)

---

### 9. Add Player Archetypes

**Implementation:**
- When adding player to roster, optionally select archetype + tech level
- Bot auto-generates stats just like for NPCs
- Saves time, ensures balance
- Players can still manually override with `/war config` if needed

**Example:**
```
/war update war_id:1 roster_action:"Add Player" side:Attacker player:@User archetype:Elite tech_level:Modern
```

Bot response:
```
✅ Added @User to Attacker side
📊 Generated stats from Elite archetype (Modern tech):
   Exosphere: 36 (30 × 1.2)
   Naval: 24 (20 × 1.2)
   Military: 60 (50 × 1.2)

Use `/war config` to manually adjust if needed.
```

---

## Final Command Structure

### `/war` - Player Commands (3)
```
/war action     - ⚔️ THE PLAYER COMMAND - Submit combat action
/war status     - View war details
/war list       - See your active wars
```

### `/war` - GM Commands (7, down from 21)
```
/war create     - Create new war (smart wizard based on type)
/war update     - Edit war (roster, settings, name, channel, etc.)
/war config     - Configure stats/archetype/theater/mode
/war modifier   - Manage combat modifiers (add/remove/list)
/war npc        - NPC management (setup/auto-resolve/escalate)
/war resolve    - Execute GM-driven combat
/war end        - Conclude war
```

### `/war` - Info Commands (1)
```
/war roster list - View rosters (read-only)
```

**Total `/war` commands: 11 (down from 21, -48% reduction!)**

---

### `/help` - NEW! (7 commands)
```
/help overview    - Bot overview
/help action      - How to use /war action
/help war         - War system guide
/help npc         - PvE and EvE guide
/help intrigue    - Intrigue guide
/help superunit   - Super unit guide
/help quick       - Quick reference card
```

---

### `/intrigue` (7, down from 8)
```
/intrigue start    - Launch operation (merged sabotage into this)
/intrigue resolve  - Execute with d20 roll
/intrigue list     - View operations
/intrigue status   - Operation details
/intrigue cancel   - Cancel operation
/intrigue intel    - View gathered intelligence
/intrigue alerts   - View detected enemy ops
```

**Removed:** `/intrigue sabotage` (redundant, merged into `/intrigue start`)

---

### `/superunit` (5, unchanged)
```
/superunit create       - Define new unit
/superunit set_intel    - Configure intel descriptions
/superunit research     - Unlock intel with roll
/superunit grant_intel  - GM manually unlocks intel
/superunit status       - View unit progress
```

**Unchanged** - already clean structure

---

### `/time` (4, down from 6)
```
/time show     - Display current time
/time set      - Set year/season
/time skip     - Advance time
/time timer    - Manage timers (add/list/cancel as sub-action)
```

**Consolidation:** Timer management uses action parameter

---

## Overall Reduction

| Command Group | Before | After | Reduction |
|---|---|---|---|
| `/war` | 21 | 11 | -48% |
| `/intrigue` | 8 | 7 | -12.5% |
| `/superunit` | 5 | 5 | 0% |
| `/time` | 6 | 4 | -33% |
| `/help` | 0 | 7 | NEW! |
| **TOTAL** | **40** | **34** | **-15%** |

**But more importantly:**
- Players only need to know **3 commands** (`/war action`, `/war status`, `/war list`)
- GMs have **logical grouping** instead of scattered commands
- **One-shot war creation** instead of 5-7 follow-up commands
- **Player archetypes** for balanced stat generation
- **Clear help system** for self-service learning

---

## Implementation Priority

### Phase 1: Help & Clarity (DONE)
- ✅ Create `/help` command system
- ✅ Improve `/war action` parameter descriptions

### Phase 2: Command Consolidation
- [ ] Consolidate `/war update` (roster, settings)
- [ ] Create `/war config` (stats, archetype, theater, mode)
- [ ] Create `/war modifier` (add/remove/list)
- [ ] Create `/war npc` (setup/auto-resolve/escalate)
- [ ] Remove redundant commands (roster_add, roster_remove, etc.)

### Phase 3: Smart War Creation
- [ ] Improve `/war create` with war_type parameter
- [ ] Add player archetype support
- [ ] Context-aware prompts based on war type

### Phase 4: Polish
- [ ] Update all documentation
- [ ] Add deprecation warnings to old commands
- [ ] Test all new workflows
- [ ] Gather user feedback

---

## Breaking Changes

The following commands will be **REMOVED**:
- `/war roster_add` → Use `/war update roster_action:Add`
- `/war roster_remove` → Use `/war update roster_action:Remove`
- `/war roster_list` → Use `/war roster list`
- `/war mention_mode` → Use `/war update mention_mode`
- `/war set_stats` → Use `/war config config_type:Stats`
- `/war set_theater` → Use `/war config config_type:Theater`
- `/war set_mode` → Use `/war config config_type:Mode`
- `/war set_npc` → Use `/war npc action:Setup`
- `/war add_modifier` → Use `/war modifier action:Add`
- `/war remove_modifier` → Use `/war modifier action:Remove`
- `/war set_auto_resolve` → Use `/war npc action:Auto-Resolve enabled:True`
- `/war stop_auto` → Use `/war npc action:Auto-Resolve enabled:False`
- `/war escalate` → Use `/war npc action:Escalate`
- `/intrigue sabotage` → Use `/intrigue start operation_type:Sabotage`
- `/time timer_add` → Use `/time timer action:Add`
- `/time timer_list` → Use `/time timer action:List`
- `/time timer_cancel` → Use `/time timer action:Cancel`

**Migration Period:** 2 weeks with deprecation warnings before removal

---

## User Communication

**Announcement template:**
```
📢 **WAR BOT UPDATE - Command Consolidation**

We've streamlined the bot to make it easier to use!

**For Players:**
✅ New `/help` system - Use `/help action` to learn how to submit combat actions
✅ `/war action` now has better descriptions explaining narrative links and rolling
✅ Only 3 commands you need to know: `/war action`, `/war status`, `/war list`

**For GMs:**
✅ Consolidated scattered commands into logical groups
✅ One-shot war creation with `/war create` (no more 5+ follow-up commands!)
✅ Player archetype support for auto-stat generation
✅ All roster/settings management in `/war update`

**What's changing:**
• Roster management moved to `/war update`
• Stats/theater/mode configuration moved to `/war config`
• Modifiers consolidated into `/war modifier`
• NPC commands grouped under `/war npc`

**Migration period:** Old commands will work for 2 weeks with deprecation warnings, then will be removed.

**Learn more:** Use `/help overview` for the new command structure!
```

---

**Status:** Phase 1 complete, ready to begin Phase 2
