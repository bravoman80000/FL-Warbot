# WAR 2.0 Deployment Checklist

## Pre-Deployment

- [x] **Backup created:** `backups/backup_2025-10-25_21-46-17/`
- [x] **Code syntax verified:** All Python files compile without errors
- [x] **Documentation updated:** PVE_SYSTEM_GUIDE.md, INTRIGUE_SYSTEM_GUIDE.md, WAR_2.0_UPDATE_SUMMARY.md

## Files Modified

### Core Systems
- [x] `warbot/core/data_manager.py` - Dual NPC config, auto-resolve tracking, backward compatibility
- [x] `warbot/core/scheduler.py` - NPC resolution loop, critical HP detection, turn limit
- [x] `warbot/core/npc_ai.py` - Dual NPC support
- [x] `warbot/bot.py` - Start NPC loop on init

### Commands
- [x] `warbot/commands/war_commands.py` - Player-driven resolution, super units, NPC config, auto-resolve, escalation
- [x] `warbot/commands/time_commands.py` - Timer autocomplete

### Documentation
- [x] `PVE_SYSTEM_GUIDE.md` - Added NPC vs NPC section
- [x] `INTRIGUE_SYSTEM_GUIDE.md` - Added rebellion gradual escalation
- [x] `WAR_2.0_UPDATE_SUMMARY.md` - Complete feature summary
- [x] `DEPLOYMENT_CHECKLIST.md` - This file

## Deployment Steps

1. **Stop the bot** (if currently running)
   ```bash
   # Kill any running bot processes
   # Or use your process manager (systemd, pm2, etc.)
   ```

2. **Verify backup exists**
   ```bash
   ls backups/backup_2025-10-25_21-46-17/
   ```

3. **Test data migration** (optional but recommended)
   ```bash
   # Make a copy of your wars.json
   cp warbot/data/wars.json warbot/data/wars.json.pre-war2

   # Start bot in test mode or with test data
   # Verify wars load correctly and migrate
   ```

4. **Start the bot**
   ```bash
   python warbot/bot.py
   # Or use your normal startup command
   ```

5. **Verify systems**
   - Bot connects to Discord
   - Commands register (may take up to 1 hour for global commands)
   - Existing wars load without errors
   - Check logs for any migration messages

## Post-Deployment Verification

### Phase 1: Basic Commands
- [ ] `/war create` - Create test war
- [ ] `/war status` - View war status
- [ ] `/war update` - Update war
- [ ] `/war end` - End test war

### Phase 2: Autocomplete
- [ ] `/war action` - War ID shows with faction names
- [ ] `/war set_npc` - War ID autocomplete works
- [ ] `/time timer_cancel` - Timer ID shows with descriptions

### Phase 3: Player-Driven Resolution
- [ ] `/war set_mode` - Set to player-driven
- [ ] `/war action` - Submit action for both sides
- [ ] Verify auto-resolution triggers
- [ ] Check results posted to channel
- [ ] Verify 12-hour cooldown

### Phase 4: Super Units
- [ ] `/war add_modifier` - Add super unit
- [ ] Use super unit in combat
- [ ] Verify +2 modifier applied
- [ ] Verify super unit removed after use

### Phase 5: PvE AI
- [ ] `/war set_npc` - Configure NPC
- [ ] Verify stats auto-generated
- [ ] Submit player action
- [ ] Verify NPC auto-responds
- [ ] Check narrative matches archetype
- [ ] Verify combat resolves

### Phase 6: NPC vs NPC
- [ ] Configure both sides as NPCs
- [ ] `/war set_auto_resolve` - Enable auto-resolve
- [ ] Wait for interval to pass (or manually trigger scheduler)
- [ ] Verify resolution occurs automatically
- [ ] Check results posted to channel
- [ ] Verify both NPCs have learning data updated

### Phase 7: War Escalation
- [ ] `/war escalate` - Convert NPC to PvE
- [ ] Verify auto-resolve stops
- [ ] Verify NPC config disabled for one side
- [ ] Add player via `/war roster add`

### Phase 8: Intrigue
- [ ] `/intrigue operation` - Launch operation
- [ ] `/intrigue list` - View operations
- [ ] `/intrigue resolve` - Resolve operation
- [ ] Verify effects applied (sabotage reduces stats)

## Rollback Procedure

If issues occur:

1. **Stop the bot immediately**
   ```bash
   # Kill bot process
   ```

2. **Restore from backup**
   ```bash
   # Copy backup back to main directory
   cp -r backups/backup_2025-10-25_21-46-17/* .
   ```

3. **Restart bot with old code**
   ```bash
   python warbot/bot.py
   ```

4. **Report issues**
   - Document what went wrong
   - Check logs for error messages
   - Note which feature caused the issue

## Known Issues to Watch For

1. **Scheduler conflicts:** If running multiple bot instances, disable auto-resolve on all but one
2. **Channel permissions:** Bot needs send permissions in war channels
3. **Command sync delay:** Global commands can take up to 1 hour to register
4. **Migration warnings:** First startup may show migration messages - this is normal

## Performance Monitoring

After deployment, monitor:

1. **CPU usage:** Hourly NPC loop should be lightweight
2. **Memory usage:** Check for memory leaks over time
3. **Response times:** Commands should respond within 2-3 seconds
4. **Error logs:** Watch for any exceptions or warnings
5. **Data file size:** wars.json and intrigue.json should grow steadily but not exponentially

## Success Criteria

Deployment is successful when:

- [x] Bot starts without errors
- [ ] All existing wars load correctly
- [ ] New commands appear in Discord
- [ ] Autocomplete works on all commands
- [ ] At least one test of each major feature works
- [ ] No critical errors in logs after 24 hours
- [ ] Community reports positive feedback

## Emergency Contacts

- **Primary GM:** Bravo
- **Co-GMs:** [Add names]
- **Bot Developer:** Claude (via Bravo)
- **Backup Location:** `backups/backup_2025-10-25_21-46-17/`

## Notes

- WAR 2.0 is a **major update** - thorough testing recommended
- **Backward compatible** - existing wars will auto-migrate
- **Documentation complete** - see WAR_2.0_UPDATE_SUMMARY.md for full details
- **Community feedback welcome** - this is a living system

---

**Deployment Status:** ⏳ Ready for deployment
**Backup Status:** ✅ Backup created
**Testing Status:** ⏳ Awaiting production testing
**Documentation Status:** ✅ Complete
