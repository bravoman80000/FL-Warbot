"""Consolidated war commands - NEW streamlined structure.

This file contains the new consolidated commands that replace scattered functionality.
After testing, these will be merged into war_commands.py and old commands removed.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Literal
import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import apply_war_defaults, find_war_by_id, load_wars, save_wars
from ..core.npc_ai import (
    ARCHETYPES,
    PERSONALITIES,
    TECH_LEVELS,
    apply_npc_config_to_war,
    generate_npc_stats,
)


class ConsolidatedWarCommands(commands.GroupCog, name="war"):
    """Consolidated war command implementations."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    def _load(self) -> List[Dict[str, Any]]:
        """Load wars from data file."""
        return load_wars()

    def _save(self, wars: List[Dict[str, Any]]) -> None:
        """Save wars to data file."""
        save_wars(wars)

    # ========== AUTOCOMPLETE FUNCTIONS ==========

    async def _war_id_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        """Autocomplete for war_id parameter - shows active wars."""
        wars = self._load()
        choices = []

        for war in wars:
            if not war.get("concluded", False):
                war_id = war.get("war_id", 0)
                name = war.get("name", f"War {war_id}")
                attacker = war.get("attacker", "?")
                defender = war.get("defender", "?")

                label = f"#{war_id}: {name} ({attacker} vs {defender})"
                if current.lower() in label.lower():
                    choices.append(app_commands.Choice(name=label[:100], value=war_id))

        return choices[:25]  # Discord limit

    async def _archetype_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for archetype parameter - shows all 20 archetypes."""
        choices = []

        for key, info in ARCHETYPES.items():
            name = info.get("name", key)
            description = info.get("description", "")[:50]

            if current.lower() in name.lower():
                label = f"{name} - {description}"
                choices.append(app_commands.Choice(name=label[:100], value=name))

        return choices[:25]

    async def _participant_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        """Autocomplete for participant removal - shows roster for selected side."""
        # This requires accessing the war_id and side from the current interaction
        # Discord.py doesn't give us access to other parameters during autocomplete
        # So we'll need to fetch all participants and let user match by name

        wars = self._load()
        choices = []

        # Try to find war from interaction namespace if available
        try:
            war_id = interaction.namespace.war_id
            war = find_war_by_id(wars, war_id)

            if war:
                # Try to get side if specified
                side = getattr(interaction.namespace, 'roster_side', None)

                if side:
                    side_key = side.lower()
                    roster_key = f"{side_key}_roster"
                    roster = war.get(roster_key, [])

                    for participant in roster:
                        member_id = participant.get("member_id")
                        name = participant.get("name", "Unknown")

                        if member_id and (current.lower() in name.lower()):
                            choices.append(
                                app_commands.Choice(name=f"{name} (ID: {member_id})", value=member_id)
                            )
        except (AttributeError, KeyError):
            # If we can't access war_id or side, return empty
            pass

        return choices[:25]

    async def _modifier_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        """Autocomplete for modifier removal - shows modifiers for selected side."""
        wars = self._load()
        choices = []

        try:
            war_id = interaction.namespace.war_id
            war = find_war_by_id(wars, war_id)

            if war:
                side = getattr(interaction.namespace, 'side', None)

                if side:
                    side_key = side.lower()
                    modifiers_key = f"{side_key}_modifiers"
                    modifiers = war.get(modifiers_key, [])

                    for modifier in modifiers:
                        mod_id = modifier.get("id")
                        mod_name = modifier.get("name", "Unknown")
                        mod_value = modifier.get("value", 0)

                        if current.lower() in mod_name.lower():
                            label = f"ID {mod_id}: {mod_name} ({mod_value:+d})"
                            choices.append(app_commands.Choice(name=label[:100], value=mod_id))
        except (AttributeError, KeyError):
            pass

        return choices[:25]

    # ========== NEW CONSOLIDATED COMMANDS ==========

    @app_commands.command(
        name="update",
        description="Update war settings, roster, name, channel, or mention mode (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.autocomplete(
        war_id=_war_id_autocomplete,
        roster_archetype=_archetype_autocomplete,
        roster_participant_id=_participant_autocomplete
    )
    @app_commands.describe(
        war_id="War ID (autocomplete shows active wars)",
        roster_action="Add or remove players from war roster",
        roster_side="Which side (Attacker or Defender)",
        roster_player="Player to add (required if Add Player)",
        roster_participant_id="Participant to remove (required if Remove Player, autocomplete shows roster)",
        roster_archetype="Optional: Archetype for auto-stat generation (NEW! works for players too!)",
        roster_tech_level="Optional: Tech level multiplier for archetype stats",
        name="Change war name",
        attacker="Change attacker faction name",
        defender="Change defender faction name",
        channel="Change war channel",
        mention_mode="How to ping players (Team Roles creates Discord roles, Individual pings each player)"
    )
    async def war_update(
        self,
        interaction: discord.Interaction,
        war_id: int,
        roster_action: Optional[Literal["Add Player", "Remove Player", "None"]] = "None",
        roster_side: Optional[Literal["Attacker", "Defender"]] = None,
        roster_player: Optional[discord.Member] = None,
        roster_participant_id: Optional[int] = None,
        roster_archetype: Optional[str] = None,
        roster_tech_level: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
        name: Optional[str] = None,
        attacker: Optional[str] = None,
        defender: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        mention_mode: Optional[Literal["Team Roles", "Individual Players"]] = None,
    ) -> None:
        """Update war configuration - consolidates roster management and settings."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!", ephemeral=True
            )
            return

        changes = []

        # === ROSTER MANAGEMENT ===
        if roster_action and roster_action != "None":
            if not roster_side:
                await interaction.response.send_message(
                    "❌ `roster_side` required when `roster_action` is not None!",
                    ephemeral=True
                )
                return

            side_key = roster_side.lower()
            roster_key = f"{side_key}_roster"

            if roster_action == "Add Player":
                if not roster_player:
                    await interaction.response.send_message(
                        "❌ `roster_player` required for Add Player action!",
                        ephemeral=True
                    )
                    return

                # Add player to roster
                participant = {
                    "name": roster_player.display_name,
                    "member_id": roster_player.id,
                }

                war[roster_key].append(participant)
                change_msg = f"• Added {roster_player.mention} to {roster_side} side"

                # NEW! Player archetype support
                if roster_archetype and roster_tech_level:
                    # Generate stats using archetype system
                    archetype_key = roster_archetype.lower().replace(" ", "_")
                    tech_key = roster_tech_level.lower().replace(" ", "_")

                    stats = generate_npc_stats(archetype_key, tech_key, base_power=50)
                    war["stats"][side_key] = stats

                    archetype_info = ARCHETYPES.get(archetype_key, {})
                    tech_info = TECH_LEVELS.get(tech_key, {})

                    change_msg += f"\n  📊 Generated stats from **{archetype_info.get('name', roster_archetype)}** archetype ({tech_info.get('name', roster_tech_level)} tech):"
                    change_msg += f"\n     Exosphere: {stats['exosphere']}, Naval: {stats['naval']}, Military: {stats['military']}"
                    change_msg += f"\n     Total Power: {sum(stats.values())}"

                changes.append(change_msg)

            elif roster_action == "Remove Player":
                if roster_participant_id is None:
                    await interaction.response.send_message(
                        "❌ `roster_participant_id` required for Remove Player action!",
                        ephemeral=True
                    )
                    return

                # Find and remove participant
                roster = war[roster_key]
                removed = False
                for i, p in enumerate(roster):
                    if p.get("member_id") == roster_participant_id:
                        removed_name = p.get("name", "Unknown")
                        roster.pop(i)
                        changes.append(f"• Removed {removed_name} from {roster_side} side")
                        removed = True
                        break

                if not removed:
                    await interaction.response.send_message(
                        f"❌ Participant ID {roster_participant_id} not found in {roster_side} roster!",
                        ephemeral=True
                    )
                    return

        # === BASIC INFO UPDATES ===
        if name:
            war["name"] = name
            changes.append(f"• War name changed to: **{name}**")

        if attacker:
            war["attacker"] = attacker
            changes.append(f"• Attacker faction changed to: **{attacker}**")

        if defender:
            war["defender"] = defender
            changes.append(f"• Defender faction changed to: **{defender}**")

        if channel:
            war["channel_id"] = channel.id
            changes.append(f"• War channel changed to: {channel.mention}")

        # === MENTION MODE ===
        if mention_mode:
            team_mentions = (mention_mode == "Team Roles")
            war["team_mentions"] = team_mentions
            changes.append(f"• Mention mode set to: **{mention_mode}**")

            # Create/remove roles if needed
            guild = interaction.guild
            if guild and team_mentions:
                # TODO: Implement role creation (from original war_commands.py)
                changes.append("  ⚠️ Team role creation not yet implemented in consolidated version")

        # Save changes
        if not changes:
            await interaction.response.send_message(
                "⚠️ No changes specified. Provide at least one parameter to update.",
                ephemeral=True
            )
            return

        self._save(wars)

        # Build response embed
        embed = discord.Embed(
            title=f"✅ War #{war_id} Updated",
            description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
            color=discord.Color.green()
        )

        embed.add_field(
            name="📋 Changes Made",
            value="\n".join(changes),
            inline=False
        )

        embed.set_footer(text=f"Use /war status war_id:{war_id} to view full war details")

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="config",
        description="Configure war stats, archetype, theater, or mode (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.autocomplete(
        war_id=_war_id_autocomplete,
        archetype=_archetype_autocomplete
    )
    @app_commands.describe(
        war_id="War ID (autocomplete shows active wars)",
        config_type="What to configure: Stats (manual), Archetype (auto-generate from doctrine), Theater (affects stat weights), or Mode (resolution type)",
        side="Which side (required for Stats/Archetype)",
        exosphere="Space/air forces stat (for Stats mode)",
        naval="Naval/water forces stat (for Stats mode)",
        military="Ground forces stat (for Stats mode)",
        archetype="Military doctrine for stat generation (20 archetypes available!)",
        tech_level="Tech era affects stat multiplier: Legacy (0.7x), Modern (1.0x), Advanced (1.2x), Cutting Edge (1.4x)",
        personality="AI personality (ONLY for NPCs - omit for player-controlled sides using archetype)",
        theater="Combat theater - affects which stats are weighted higher in combat",
        mode="Resolution mode: Player-Driven (auto), GM-Driven (manual), or NPC Auto-Resolve (EvE only)",
        cooldown_hours="Hours between player actions (only for Player-Driven mode)"
    )
    async def war_config(
        self,
        interaction: discord.Interaction,
        war_id: int,
        config_type: Literal["Stats", "Archetype", "Theater", "Mode"],
        side: Optional[Literal["Attacker", "Defender"]] = None,
        exosphere: Optional[int] = None,
        naval: Optional[int] = None,
        military: Optional[int] = None,
        archetype: Optional[str] = None,
        tech_level: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
        personality: Optional[Literal["Aggressive", "Defensive", "Adaptive", "Balanced", "Berserker"]] = None,
        theater: Optional[Literal["Exosphere", "Naval", "Land", "Multi-Theater"]] = None,
        mode: Optional[Literal["Player-Driven", "GM-Driven", "NPC Auto-Resolve"]] = None,
        cooldown_hours: Optional[int] = 12,
    ) -> None:
        """Configure war settings - consolidates stats, archetype, theater, and mode configuration."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"✅ War #{war_id} Configuration Updated",
            description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
            color=discord.Color.blue()
        )

        # === STATS MODE ===
        if config_type == "Stats":
            if not side:
                await interaction.response.send_message(
                    "❌ `side` required for Stats configuration!", ephemeral=True
                )
                return

            if exosphere is None or naval is None or military is None:
                await interaction.response.send_message(
                    "❌ All three stats (exosphere, naval, military) required for Stats mode!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            war["stats"][side_key] = {
                "exosphere": exosphere,
                "naval": naval,
                "military": military
            }

            embed.add_field(
                name=f"📊 Stats Updated: {side} Side",
                value=f"Exosphere: {exosphere}\nNaval: {naval}\nMilitary: {military}\n\n**Total Power:** {exosphere + naval + military}",
                inline=False
            )

        # === ARCHETYPE MODE ===
        elif config_type == "Archetype":
            if not side or not archetype or not tech_level:
                await interaction.response.send_message(
                    "❌ `side`, `archetype`, and `tech_level` required for Archetype configuration!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            archetype_key = archetype.lower().replace(" ", "_")
            tech_key = tech_level.lower().replace(" ", "_")

            # Generate stats
            stats = generate_npc_stats(archetype_key, tech_key, base_power=50)
            war["stats"][side_key] = stats

            archetype_info = ARCHETYPES.get(archetype_key, {})
            tech_info = TECH_LEVELS.get(tech_key, {})

            # If personality provided: Mark as NPC
            if personality:
                apply_npc_config_to_war(war, side_key, archetype_key, tech_key, personality.lower())

                embed.add_field(
                    name=f"🤖 NPC Configured: {side} Side",
                    value=f"**{archetype_info.get('name', archetype)}** ({tech_info.get('name', tech_level)} Tech, {personality})",
                    inline=False
                )

                # Calculate aggression
                base_aggression = archetype_info.get('aggression', 0.5)
                personality_info = PERSONALITIES.get(personality.lower(), {})
                personality_mod = personality_info.get('aggression_modifier', 0.0)
                total_aggression = base_aggression + personality_mod

                embed.add_field(
                    name="⚡ AI Behavior",
                    value=f"Aggression: {total_aggression:.2f}\nThis side is NPC-controlled and will auto-respond to player actions.",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"📊 Archetype Applied: {side} Side",
                    value=f"**{archetype_info.get('name', archetype)}** ({tech_info.get('name', tech_level)} Tech)",
                    inline=False
                )
                embed.add_field(
                    name="👤 Player-Controlled",
                    value="This side uses archetype stats but remains player-controlled (no personality = no AI).",
                    inline=False
                )

            embed.add_field(
                name="📈 Generated Stats",
                value=f"Exosphere: {stats['exosphere']}\nNaval: {stats['naval']}\nMilitary: {stats['military']}\n\n**Total Power:** {sum(stats.values())}",
                inline=False
            )

            if archetype_info.get('description'):
                embed.add_field(
                    name="📖 Archetype Description",
                    value=archetype_info['description'],
                    inline=False
                )

        # === THEATER MODE ===
        elif config_type == "Theater":
            if not theater:
                await interaction.response.send_message(
                    "❌ `theater` required for Theater configuration!", ephemeral=True
                )
                return

            war["theater"] = theater

            theater_effects = {
                "Exosphere": "Exosphere stat weighted **50%** (primary), Naval/Military **25%** each (supporting)",
                "Naval": "Naval stat weighted **50%** (primary), Exosphere/Military **25%** each (supporting)",
                "Land": "Military stat weighted **50%** (primary), Exosphere/Naval **25%** each (supporting)",
                "Multi-Theater": "All stats weighted **equally** (33/33/33) - combined arms warfare"
            }

            embed.add_field(
                name=f"🗺️ Theater Set: {theater}",
                value=theater_effects.get(theater, "Theater effects not defined"),
                inline=False
            )

            embed.add_field(
                name="💡 Strategic Implications",
                value="Choose theater based on your faction's stat strengths. Theater doesn't change stats, but affects how heavily each stat counts in combat calculations.",
                inline=False
            )

        # === MODE MODE ===
        elif config_type == "Mode":
            if not mode:
                await interaction.response.send_message(
                    "❌ `mode` required for Mode configuration!", ephemeral=True
                )
                return

            # Validate mode choice
            if mode == "NPC Auto-Resolve":
                # Check if both sides are NPCs
                npc_config = war.get("npc_config", {})
                attacker_is_npc = npc_config.get("attacker", {}).get("enabled", False)
                defender_is_npc = npc_config.get("defender", {}).get("enabled", False)

                if not (attacker_is_npc and defender_is_npc):
                    await interaction.response.send_message(
                        "❌ NPC Auto-Resolve mode requires BOTH sides to be NPC-controlled!\n"
                        "Use `/war config config_type:Archetype` with personality to set up NPCs first.",
                        ephemeral=True
                    )
                    return

            mode_map = {
                "Player-Driven": "player_driven",
                "GM-Driven": "gm_driven",
                "NPC Auto-Resolve": "npc_auto_resolve"
            }

            war["resolution_mode"] = mode_map[mode]

            if mode == "Player-Driven":
                war["resolution_cooldown_hours"] = cooldown_hours

            mode_descriptions = {
                "Player-Driven": f"Players use `/war action` to submit actions, auto-resolves when both sides submit (cooldown: {cooldown_hours}h)",
                "GM-Driven": "GMs use `/war resolve` to manually execute each turn with action selection UI",
                "NPC Auto-Resolve": "Both NPCs fight autonomously, resolving every 12 hours (configure via `/war npc action:Auto-Resolve`)"
            }

            embed.add_field(
                name=f"⚙️ Mode Set: {mode}",
                value=mode_descriptions[mode],
                inline=False
            )

        self._save(wars)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="modifier",
        description="Manage combat modifiers: add, remove, or list (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.autocomplete(
        war_id=_war_id_autocomplete,
        modifier_id=_modifier_autocomplete
    )
    @app_commands.describe(
        war_id="War ID (autocomplete shows active wars)",
        action="Add a new modifier, Remove an existing one, or List all modifiers",
        side="Which side (required for Add/Remove)",
        name="Modifier name/description (required for Add)",
        value="Modifier value - positive for bonus, negative for penalty (required for Add)",
        duration="How long the modifier lasts",
        modifier_id="Which modifier to remove (autocomplete shows active modifiers)"
    )
    async def war_modifier(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["Add", "Remove", "List"],
        side: Optional[Literal["Attacker", "Defender"]] = None,
        name: Optional[str] = None,
        value: Optional[int] = None,
        duration: Optional[Literal["Permanent", "Next Resolution", "2 Turns", "3 Turns", "5 Turns"]] = "Permanent",
        modifier_id: Optional[int] = None,
    ) -> None:
        """Manage combat modifiers - consolidates add/remove with new list capability."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🎯 Modifiers: War #{war_id}",
            description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
            color=discord.Color.gold()
        )

        # === ADD ACTION ===
        if action == "Add":
            if not side or not name or value is None:
                await interaction.response.send_message(
                    "❌ `side`, `name`, and `value` required for Add action!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            modifiers_key = f"{side_key}_modifiers"

            # Initialize modifiers list if not exists
            if modifiers_key not in war:
                war[modifiers_key] = []

            # Generate unique ID
            existing_ids = [m.get("id", 0) for m in war.get(modifiers_key, [])]
            new_id = max(existing_ids, default=0) + 1

            # Add modifier
            modifier = {
                "id": new_id,
                "name": name,
                "value": value,
                "duration": duration,
                "turns_remaining": self._duration_to_turns(duration)
            }

            war[modifiers_key].append(modifier)

            embed.add_field(
                name=f"✅ Modifier Added: {side} Side",
                value=f"**{name}** ({value:+d})\nDuration: {duration}",
                inline=False
            )

            # Show current total
            total = sum(m.get("value", 0) for m in war.get(modifiers_key, []))
            embed.add_field(
                name=f"📊 {side} Total Modifiers",
                value=f"{total:+d}",
                inline=True
            )

        # === REMOVE ACTION ===
        elif action == "Remove":
            if not side or modifier_id is None:
                await interaction.response.send_message(
                    "❌ `side` and `modifier_id` required for Remove action!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            modifiers_key = f"{side_key}_modifiers"

            modifiers = war.get(modifiers_key, [])
            removed = None

            for i, m in enumerate(modifiers):
                if m.get("id") == modifier_id:
                    removed = modifiers.pop(i)
                    break

            if not removed:
                await interaction.response.send_message(
                    f"❌ Modifier ID {modifier_id} not found in {side} modifiers!",
                    ephemeral=True
                )
                return

            embed.add_field(
                name=f"🗑️ Modifier Removed: {side} Side",
                value=f"**{removed.get('name')}** ({removed.get('value'):+d})",
                inline=False
            )

            # Show new total
            total = sum(m.get("value", 0) for m in war.get(modifiers_key, []))
            embed.add_field(
                name=f"📊 {side} Total Modifiers",
                value=f"{total:+d}",
                inline=True
            )

        # === LIST ACTION ===
        elif action == "List":
            # List modifiers for both sides
            for side_name in ["Attacker", "Defender"]:
                side_key = side_name.lower()
                modifiers_key = f"{side_key}_modifiers"
                modifiers = war.get(modifiers_key, [])

                if modifiers:
                    modifier_list = []
                    for m in modifiers:
                        mid = m.get("id", "?")
                        mname = m.get("name", "Unknown")
                        mvalue = m.get("value", 0)
                        mduration = m.get("duration", "Permanent")
                        modifier_list.append(f"• ID {mid}: **{mname}** ({mvalue:+d}, {mduration})")

                    total = sum(m.get("value", 0) for m in modifiers)
                    modifier_text = "\n".join(modifier_list) + f"\n\n**Total:** {total:+d}"
                else:
                    modifier_text = "No modifiers"

                embed.add_field(
                    name=f"🔸 {side_name} Modifiers",
                    value=modifier_text,
                    inline=False
                )

        self._save(wars)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    def _duration_to_turns(self, duration: str) -> Optional[int]:
        """Convert duration string to turns remaining."""
        duration_map = {
            "Permanent": None,
            "Next Resolution": 1,
            "2 Turns": 2,
            "3 Turns": 3,
            "5 Turns": 5,
        }
        return duration_map.get(duration)

    @app_commands.command(
        name="npc",
        description="Manage NPC sides: setup, auto-resolution, or escalation (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.autocomplete(
        war_id=_war_id_autocomplete,
        archetype=_archetype_autocomplete
    )
    @app_commands.describe(
        war_id="War ID (autocomplete shows active wars)",
        action="Setup NPC side, enable/disable auto-resolution, or escalate war to PvE/PvP",
        side="Which side to configure as NPC (required for Setup)",
        archetype="Military doctrine for NPC (20 archetypes available!)",
        tech_level="Tech era affects stat multiplier",
        personality="AI personality determines tactics and aggression (required for Setup)",
        enabled="Enable or disable auto-resolution (required for Auto-Resolve action)",
        interval_hours="Hours between auto-resolutions (default: 12)",
        max_turns="Maximum turns before defender victory (default: 50)",
        escalation_type="To PvE (one NPC → player) or To PvP (both NPCs → players)",
        new_mode="New resolution mode after escalation"
    )
    async def war_npc(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["Setup", "Auto-Resolve", "Escalate"],
        side: Optional[Literal["Attacker", "Defender"]] = None,
        archetype: Optional[str] = None,
        tech_level: Optional[Literal["Legacy", "Modern", "Advanced", "Cutting Edge"]] = None,
        personality: Optional[Literal["Aggressive", "Defensive", "Adaptive", "Balanced", "Berserker"]] = None,
        enabled: Optional[bool] = None,
        interval_hours: Optional[int] = 12,
        max_turns: Optional[int] = 50,
        escalation_type: Optional[Literal["To PvE", "To PvP"]] = None,
        new_mode: Optional[Literal["Player-Driven", "GM-Driven"]] = None,
    ) -> None:
        """Manage NPC configuration - consolidates setup, auto-resolve, and escalation."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🤖 NPC Management: War #{war_id}",
            description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
            color=discord.Color.purple()
        )

        # === SETUP ACTION ===
        if action == "Setup":
            if not side or not archetype or not tech_level or not personality:
                await interaction.response.send_message(
                    "❌ `side`, `archetype`, `tech_level`, and `personality` required for Setup action!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            archetype_key = archetype.lower().replace(" ", "_")
            tech_key = tech_level.lower().replace(" ", "_")
            personality_key = personality.lower()

            # Generate stats and apply NPC config
            stats = generate_npc_stats(archetype_key, tech_key, base_power=50)
            war["stats"][side_key] = stats

            apply_npc_config_to_war(war, side_key, archetype_key, tech_key, personality_key)

            archetype_info = ARCHETYPES.get(archetype_key, {})
            tech_info = TECH_LEVELS.get(tech_key, {})
            personality_info = PERSONALITIES.get(personality_key, {})

            # Calculate aggression
            base_aggression = archetype_info.get('aggression', 0.5)
            personality_mod = personality_info.get('aggression_modifier', 0.0)
            total_aggression = base_aggression + personality_mod

            embed.add_field(
                name=f"✅ NPC Configured: {side} Side",
                value=f"🤖 **{archetype_info.get('name', archetype)}** ({tech_info.get('name', tech_level)} Tech, {personality})",
                inline=False
            )

            embed.add_field(
                name="📊 Generated Stats",
                value=(
                    f"• Exosphere: {stats['exosphere']}\n"
                    f"• Naval: {stats['naval']}\n"
                    f"• Military: {stats['military']}\n\n"
                    f"**Total Power:** {sum(stats.values())}"
                ),
                inline=False
            )

            embed.add_field(
                name="⚡ AI Behavior",
                value=f"**Aggression:** {total_aggression:.2f}\nThis side is NPC-controlled and will auto-respond to player actions.",
                inline=False
            )

            if archetype_info.get('description'):
                embed.add_field(
                    name="📖 Archetype Traits",
                    value=archetype_info['description'],
                    inline=False
                )

            # Check if both sides are now NPCs
            npc_config = war.get("npc_config", {})
            attacker_is_npc = npc_config.get("attacker", {}).get("enabled", False)
            defender_is_npc = npc_config.get("defender", {}).get("enabled", False)

            if attacker_is_npc and defender_is_npc:
                embed.add_field(
                    name="⚠️ Both Sides Now NPC-Controlled!",
                    value=f"Use `/war npc action:Auto-Resolve war_id:{war_id} enabled:True` to enable autonomous war resolution.",
                    inline=False
                )

        # === AUTO-RESOLVE ACTION ===
        elif action == "Auto-Resolve":
            if enabled is None:
                await interaction.response.send_message(
                    "❌ `enabled` required for Auto-Resolve action!",
                    ephemeral=True
                )
                return

            # Validate both sides are NPCs
            npc_config = war.get("npc_config", {})
            attacker_is_npc = npc_config.get("attacker", {}).get("enabled", False)
            defender_is_npc = npc_config.get("defender", {}).get("enabled", False)

            if not (attacker_is_npc and defender_is_npc):
                await interaction.response.send_message(
                    "❌ Both sides must be NPC-controlled to enable auto-resolution!\n"
                    "Use `/war npc action:Setup` to configure NPCs first.",
                    ephemeral=True
                )
                return

            if enabled:
                # Enable auto-resolution
                war["resolution_mode"] = "npc_auto_resolve"
                war["auto_resolve_enabled"] = True
                war["auto_resolve_interval_hours"] = interval_hours
                war["auto_resolve_max_turns"] = max_turns

                # Calculate next resolution time
                import time
                next_resolve_time = int(time.time()) + (interval_hours * 3600)

                embed.add_field(
                    name="✅ NPC Auto-Resolution Enabled",
                    value="🤖 War will now resolve autonomously in the background!",
                    inline=False
                )

                embed.add_field(
                    name="⚙️ Configuration",
                    value=(
                        f"• **Interval:** Every {interval_hours} hours\n"
                        f"• **Max Turns:** {max_turns} (defender wins if reached)\n"
                        f"• **Critical HP:** GM pinged when either side near death"
                    ),
                    inline=False
                )

                embed.add_field(
                    name="⏰ Next Resolution",
                    value=f"<t:{next_resolve_time}:R> (in ~{interval_hours} hours)",
                    inline=False
                )

            else:
                # Disable auto-resolution
                war["auto_resolve_enabled"] = False

                embed.add_field(
                    name="⏸️ NPC Auto-Resolution Disabled",
                    value="Auto-resolution has been stopped. War remains NPC vs NPC but won't auto-resolve.",
                    inline=False
                )

                embed.add_field(
                    name="💡 Next Steps",
                    value=(
                        "• Use `/war resolve` to manually resolve turns\n"
                        "• Or use `/war npc action:Escalate` to convert to PvE/PvP"
                    ),
                    inline=False
                )

        # === ESCALATE ACTION ===
        elif action == "Escalate":
            if not escalation_type or not new_mode:
                await interaction.response.send_message(
                    "❌ `escalation_type` and `new_mode` required for Escalate action!",
                    ephemeral=True
                )
                return

            npc_config = war.get("npc_config", {})
            changes_made = []

            if escalation_type == "To PvE":
                # Disable one NPC side (user needs to specify which or we pick defender)
                # For simplicity, disable defender side
                if npc_config.get("defender", {}).get("enabled", False):
                    npc_config["defender"]["enabled"] = False
                    changes_made.append("• Defender NPC disabled (now player-controlled)")
                elif npc_config.get("attacker", {}).get("enabled", False):
                    npc_config["attacker"]["enabled"] = False
                    changes_made.append("• Attacker NPC disabled (now player-controlled)")
                else:
                    await interaction.response.send_message(
                        "❌ No NPC sides found to escalate from!",
                        ephemeral=True
                    )
                    return

                war["auto_resolve_enabled"] = False
                changes_made.append("• Auto-resolution stopped")

            elif escalation_type == "To PvP":
                # Disable both NPC sides
                if npc_config.get("attacker", {}).get("enabled", False):
                    npc_config["attacker"]["enabled"] = False
                    changes_made.append("• Attacker NPC disabled")

                if npc_config.get("defender", {}).get("enabled", False):
                    npc_config["defender"]["enabled"] = False
                    changes_made.append("• Defender NPC disabled")

                war["auto_resolve_enabled"] = False
                changes_made.append("• Auto-resolution stopped")

            # Change resolution mode
            mode_map = {
                "Player-Driven": "player_driven",
                "GM-Driven": "gm_driven"
            }
            war["resolution_mode"] = mode_map[new_mode]
            changes_made.append(f"• Mode changed to **{new_mode}**")

            embed.add_field(
                name=f"✅ War Escalated {escalation_type}",
                value=f"War has been escalated from NPC vs NPC to {escalation_type.replace('To ', '')}",
                inline=False
            )

            embed.add_field(
                name="📈 Changes Made",
                value="\n".join(changes_made),
                inline=False
            )

            embed.add_field(
                name="📋 Next Steps",
                value=(
                    "1. Use `/war update roster_action:Add` to add players to now-player-controlled sides\n"
                    "2. Players use `/war action` to submit combat actions (if Player-Driven)\n"
                    "3. Former NPC sides now require player input"
                ),
                inline=False
            )

        self._save(wars)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="roster",
        description="View war rosters for both sides (read-only)"
    )
    @app_commands.guild_only()
    @app_commands.autocomplete(war_id=_war_id_autocomplete)
    @app_commands.describe(
        war_id="War ID (autocomplete shows active wars)",
        action="List shows all participants on both sides"
    )
    async def war_roster(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["list"] = "list"
    ) -> None:
        """View war rosters - read-only command to see participants."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"📋 War #{war_id} Rosters",
            description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
            color=discord.Color.blue()
        )

        # Attacker roster
        attacker_roster = war.get("attacker_roster", [])
        if attacker_roster:
            roster_lines = []
            for participant in attacker_roster:
                name = participant.get("name", "Unknown")
                member_id = participant.get("member_id")
                if member_id:
                    roster_lines.append(f"• <@{member_id}> ({name})")
                else:
                    roster_lines.append(f"• {name}")

            embed.add_field(
                name=f"⚔️ {war.get('attacker', 'Attacker')} Roster",
                value="\n".join(roster_lines) if roster_lines else "No participants",
                inline=False
            )
        else:
            embed.add_field(
                name=f"⚔️ {war.get('attacker', 'Attacker')} Roster",
                value="No participants",
                inline=False
            )

        # Defender roster
        defender_roster = war.get("defender_roster", [])
        if defender_roster:
            roster_lines = []
            for participant in defender_roster:
                name = participant.get("name", "Unknown")
                member_id = participant.get("member_id")
                if member_id:
                    roster_lines.append(f"• <@{member_id}> ({name})")
                else:
                    roster_lines.append(f"• {name}")

            embed.add_field(
                name=f"🛡️ {war.get('defender', 'Defender')} Roster",
                value="\n".join(roster_lines) if roster_lines else "No participants",
                inline=False
            )
        else:
            embed.add_field(
                name=f"🛡️ {war.get('defender', 'Defender')} Roster",
                value="No participants",
                inline=False
            )

        # Mention mode info
        team_mentions = war.get("team_mentions", False)
        mention_mode = "Team Roles" if team_mentions else "Individual Players"

        embed.add_field(
            name="📢 Mention Mode",
            value=f"Currently set to: **{mention_mode}**",
            inline=False
        )

        embed.set_footer(text=f"Use /war update to add/remove players or change mention mode")

        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    """Register the consolidated war commands cog."""
    await bot.add_cog(ConsolidatedWarCommands(bot))
