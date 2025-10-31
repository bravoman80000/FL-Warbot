"""Fully consolidated war commands - OPERATION GREENLIGHT 2.0

All war commands restructured into clean action-based groups:
- /war manage - Create, End, Status wars
- /war battle - Resolve, Next turn
- /war roster - Add, Remove, List players
- /war settings - Mode, Name, Channel, Mention
- /war theater - Add, Remove, Close, Reopen, Rename, List theaters
- /war subhp - Add, Remove, Damage, Heal, Rename, List sub-healthbars
- /war modifier - Add, Remove, List combat modifiers
- /war npc - Setup, Auto-Resolve, Escalate NPC sides
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import find_war_by_id, load_wars, save_wars, apply_war_defaults
from ..core.subbar_manager import (
    add_subhp,
    add_theater,
    apply_subhp_damage,
    apply_subhp_heal,
    close_theater,
    find_subhp_by_id,
    find_theater_by_id,
    remove_subhp,
    remove_theater,
    reopen_theater,
)

# Note: We'll import other needed functions as we build each command group


class ConsolidatedWarCommandsV2(commands.GroupCog, name="war"):
    """Fully consolidated war commands - clean action-based structure."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    def _load(self) -> List[Dict[str, Any]]:
        """Load wars from data file."""
        return load_wars()

    def _save(self, wars: List[Dict[str, Any]]) -> None:
        """Save wars to data file."""
        save_wars(wars)

    def _next_war_id(self, wars: List[Dict[str, Any]]) -> int:
        """Generate next war ID."""
        if not wars:
            return 1
        return max(w.get("id", 0) for w in wars) + 1

    # ========== /war manage - Create, End, Status ==========

    @app_commands.command(
        name="manage",
        description="🎯 Manage wars - Create new, End existing, or view Status (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        action="What to do: Create new war, End war, or view Status",
        war_id="War ID (for End/Status actions)",
        attacker="Attacker faction name (for Create)",
        defender="Defender faction name (for Create)",
        name="Custom war name (for Create, optional)",
        channel="War channel (for Create, defaults to current)",
        mode="War mode: Push-Pull, One-Way, or Attrition (for Create)",
        max_value="Max warbar value (for Create, default 100)",
        attacker_health="Attacker starting HP for Attrition mode",
        defender_health="Defender starting HP for Attrition mode"
    )
    async def war_manage(
        self,
        interaction: discord.Interaction,
        action: Literal["Create", "End", "Status"],
        war_id: Optional[int] = None,
        attacker: Optional[str] = None,
        defender: Optional[str] = None,
        name: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        mode: Optional[Literal["Push-Pull Manual", "One-Way Manual", "Attrition Manual"]] = None,
        max_value: Optional[int] = 100,
        attacker_health: Optional[int] = 100,
        defender_health: Optional[int] = 100,
    ) -> None:
        """Manage wars - create, end, or view status."""
        wars = self._load()

        # === CREATE WAR ===
        if action == "Create":
            if not attacker or not defender:
                await interaction.response.send_message(
                    "❌ `attacker` and `defender` required for Create action!",
                    ephemeral=True
                )
                return

            war_id = self._next_war_id(wars)
            war_name = name or f"{attacker} vs {defender}"
            channel_id = (channel or interaction.channel).id

            # Map mode to internal value
            mode_map = {
                "Push-Pull Manual": "pushpull_manual",
                "One-Way Manual": "oneway_manual",
                "Attrition Manual": "attrition_manual"
            }
            internal_mode = mode_map.get(mode, "pushpull_manual")

            war = {
                "id": war_id,
                "name": war_name,
                "attacker": attacker,
                "defender": defender,
                "mode": internal_mode,
                "warbar": 0,
                "max_value": max_value,
                "momentum": 0,
                "initiative": "attacker",
                "channel_id": channel_id,
                "attacker_roster": [],
                "defender_roster": [],
                "attacker_turn_index": 0,
                "defender_turn_index": 0,
                "team_mentions": False,
                "attacker_role_id": None,
                "defender_role_id": None,
                "concluded": False,
            }

            # Attrition mode specific fields
            if internal_mode == "attrition_manual":
                war["attacker_max_health"] = attacker_health
                war["defender_max_health"] = defender_health
                war["attacker_health"] = attacker_health
                war["defender_health"] = defender_health

            # Apply defaults (adds theaters, subhps, etc.)
            apply_war_defaults(war)

            wars.append(war)
            self._save(wars)

            embed = discord.Embed(
                title=f"✅ War Created: {war_name}",
                description=f"**{attacker}** vs **{defender}**",
                color=discord.Color.green()
            )

            embed.add_field(name="War ID", value=str(war_id), inline=True)
            embed.add_field(name="Mode", value=mode or "Push-Pull Manual", inline=True)
            embed.add_field(name="Max Value", value=str(max_value), inline=True)
            embed.add_field(name="Channel", value=f"<#{channel_id}>", inline=True)

            embed.add_field(
                name="📋 Next Steps",
                value=(
                    f"• Add players: `/war roster action:Add war_id:{war_id}`\n"
                    f"• Add theaters: `/war theater action:Add war_id:{war_id}`\n"
                    f"• Configure settings: `/war settings war_id:{war_id}`\n"
                    f"• Set up NPCs: `/war npc action:Setup war_id:{war_id}`"
                ),
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        # === END WAR ===
        elif action == "End":
            if war_id is None:
                await interaction.response.send_message(
                    "❌ `war_id` required for End action!",
                    ephemeral=True
                )
                return

            war = find_war_by_id(wars, war_id)
            if not war:
                await interaction.response.send_message(
                    f"❌ War with ID {war_id} not found!",
                    ephemeral=True
                )
                return

            war_name = war.get("name", f"War #{war_id}")

            # Mark as concluded instead of deleting
            war["concluded"] = True
            self._save(wars)

            embed = discord.Embed(
                title=f"🏁 War Ended: {war_name}",
                color=discord.Color.orange()
            )

            embed.add_field(
                name="Final Status",
                value=f"Warbar: {war.get('warbar', 0):+d}/{war.get('max_value', 100)}",
                inline=False
            )

            await interaction.response.send_message(embed=embed)

        # === STATUS ===
        elif action == "Status":
            if war_id is None:
                await interaction.response.send_message(
                    "❌ `war_id` required for Status action!",
                    ephemeral=True
                )
                return

            war = find_war_by_id(wars, war_id)
            if not war:
                await interaction.response.send_message(
                    f"❌ War with ID {war_id} not found!",
                    ephemeral=True
                )
                return

            # TODO: Build comprehensive status embed
            # This will show: warbar, theaters, sub-HPs, rosters, modifiers, etc.
            # For now, basic status:

            embed = discord.Embed(
                title=f"📊 War Status: {war.get('name', f'War #{war_id}')}",
                description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
                color=discord.Color.blue()
            )

            # Warbar
            warbar = war.get("warbar", 0)
            max_val = war.get("max_value", 100)
            embed.add_field(
                name="📈 Main Warbar",
                value=f"{warbar:+d}/{max_val}",
                inline=True
            )

            # Mode
            mode = war.get("resolution_mode", war.get("mode", "gm_driven"))
            embed.add_field(
                name="⚙️ Resolution Mode",
                value=mode.replace("_", " ").title(),
                inline=True
            )

            # Theaters
            theaters = war.get("theaters", [])
            embed.add_field(
                name="🗺️ Theaters",
                value=f"{len(theaters)} configured" if theaters else "None",
                inline=True
            )

            # TODO: Add more detail (rosters, modifiers, etc.)

            embed.set_footer(text=f"War ID: {war_id} | Use /war theater action:List to see theater details")

            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ========== /war battle - Resolve, Next ==========

    @app_commands.command(
        name="battle",
        description="⚔️ War turn management - Resolve combat or advance Next turn (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        war_id="War ID",
        action="Resolve combat turn or advance to Next side's turn"
    )
    async def war_battle(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["Resolve", "Next"],
    ) -> None:
        """Manage war turns - resolve combat or advance initiative."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if not war:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!",
                ephemeral=True
            )
            return

        if action == "Resolve":
            # TODO: Launch resolution UI
            # For now, placeholder
            await interaction.response.send_message(
                f"🎮 Resolve action for War #{war_id} coming soon!\n"
                f"This will launch the GM action selection UI.",
                ephemeral=True
            )

        elif action == "Next":
            # Flip initiative
            current = war.get("initiative", "attacker")
            new_init = "defender" if current == "attacker" else "attacker"
            war["initiative"] = new_init

            self._save(wars)

            await interaction.response.send_message(
                f"✅ Initiative advanced to **{new_init.title()}** for {war.get('name', f'War #{war_id}')}",
                ephemeral=True
            )

    # ========== /war roster - Add, Remove, List ==========

    @app_commands.command(
        name="roster",
        description="📋 Manage war rosters - Add/Remove players or List participants (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        war_id="War ID",
        action="Add player, Remove player, or List all participants",
        side="Which side (Attacker or Defender)",
        player="Player to add (for Add action)",
        participant_id="Participant to remove (for Remove action)"
    )
    async def war_roster(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["Add", "Remove", "List"],
        side: Optional[Literal["Attacker", "Defender"]] = None,
        player: Optional[discord.Member] = None,
        participant_id: Optional[int] = None,
    ) -> None:
        """Manage war rosters."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if not war:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!",
                ephemeral=True
            )
            return

        # === ADD PLAYER ===
        if action == "Add":
            if not side or not player:
                await interaction.response.send_message(
                    "❌ `side` and `player` required for Add action!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            roster_key = f"{side_key}_roster"

            participant = {
                "name": player.display_name,
                "member_id": player.id,
            }

            war[roster_key].append(participant)
            self._save(wars)

            await interaction.response.send_message(
                f"✅ Added **{player.display_name}** to {side} roster for {war.get('name', f'War #{war_id}')}",
                ephemeral=True
            )

        # === REMOVE PLAYER ===
        elif action == "Remove":
            if not side or participant_id is None:
                await interaction.response.send_message(
                    "❌ `side` and `participant_id` required for Remove action!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            roster_key = f"{side_key}_roster"
            roster = war.get(roster_key, [])

            removed = None
            for i, p in enumerate(roster):
                if p.get("member_id") == participant_id:
                    removed = roster.pop(i)
                    break

            if not removed:
                await interaction.response.send_message(
                    f"❌ Participant ID {participant_id} not found in {side} roster!",
                    ephemeral=True
                )
                return

            self._save(wars)

            await interaction.response.send_message(
                f"✅ Removed **{removed.get('name')}** from {side} roster",
                ephemeral=True
            )

        # === LIST ROSTER ===
        elif action == "List":
            embed = discord.Embed(
                title=f"📋 War Rosters: {war.get('name', f'War #{war_id}')}",
                description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
                color=discord.Color.blue()
            )

            # Attacker roster
            attacker_roster = war.get("attacker_roster", [])
            if attacker_roster:
                lines = [f"• <@{p['member_id']}>" for p in attacker_roster if p.get("member_id")]
                embed.add_field(
                    name=f"⚔️ {war.get('attacker', 'Attacker')} Roster ({len(attacker_roster)})",
                    value="\n".join(lines) if lines else "No participants",
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
                lines = [f"• <@{p['member_id']}>" for p in defender_roster if p.get("member_id")]
                embed.add_field(
                    name=f"🛡️ {war.get('defender', 'Defender')} Roster ({len(defender_roster)})",
                    value="\n".join(lines) if lines else "No participants",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"🛡️ {war.get('defender', 'Defender')} Roster",
                    value="No participants",
                    inline=False
                )

            await interaction.response.send_message(embed=embed, ephemeral=True)

    # ========== /war settings - Mode, Name, Channel, Mention ==========

    @app_commands.command(
        name="settings",
        description="⚙️ Configure war settings - Mode, Name, Channel, Mention style (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        war_id="War ID",
        action="What to change: Resolution Mode, War Name, Channel, or Mention style",
        resolution_mode="Resolution mode (for Mode action)",
        cooldown_hours="Cooldown between player actions (for Mode action)",
        war_name="New war name (for Name action)",
        channel="New war channel (for Channel action)",
        mention_style="How to ping players (for Mention action)"
    )
    async def war_settings(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["Mode", "Name", "Channel", "Mention"],
        resolution_mode: Optional[Literal["GM-Driven", "Player-Driven"]] = None,
        cooldown_hours: Optional[int] = 12,
        war_name: Optional[str] = None,
        channel: Optional[discord.TextChannel] = None,
        mention_style: Optional[Literal["Team Roles", "Individual Players"]] = None,
    ) -> None:
        """Configure war settings."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if not war:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!",
                ephemeral=True
            )
            return

        # === MODE ===
        if action == "Mode":
            if not resolution_mode:
                await interaction.response.send_message(
                    "❌ `resolution_mode` required for Mode action!",
                    ephemeral=True
                )
                return

            mode_map = {
                "GM-Driven": "gm_driven",
                "Player-Driven": "player_driven"
            }

            war["resolution_mode"] = mode_map[resolution_mode]
            if resolution_mode == "Player-Driven":
                war["resolution_cooldown_hours"] = cooldown_hours

            self._save(wars)

            await interaction.response.send_message(
                f"✅ Resolution mode set to **{resolution_mode}** for War #{war_id}\n"
                f"{'Cooldown: ' + str(cooldown_hours) + 'h' if resolution_mode == 'Player-Driven' else ''}",
                ephemeral=True
            )

        # === NAME ===
        elif action == "Name":
            if not war_name:
                await interaction.response.send_message(
                    "❌ `war_name` required for Name action!",
                    ephemeral=True
                )
                return

            old_name = war.get("name")
            war["name"] = war_name
            self._save(wars)

            await interaction.response.send_message(
                f"✅ War name changed: **{old_name}** → **{war_name}**",
                ephemeral=True
            )

        # === CHANNEL ===
        elif action == "Channel":
            if not channel:
                await interaction.response.send_message(
                    "❌ `channel` required for Channel action!",
                    ephemeral=True
                )
                return

            war["channel_id"] = channel.id
            self._save(wars)

            await interaction.response.send_message(
                f"✅ War channel changed to {channel.mention} for War #{war_id}",
                ephemeral=True
            )

        # === MENTION ===
        elif action == "Mention":
            if not mention_style:
                await interaction.response.send_message(
                    "❌ `mention_style` required for Mention action!",
                    ephemeral=True
                )
                return

            team_mentions = (mention_style == "Team Roles")
            war["team_mentions"] = team_mentions
            self._save(wars)

            await interaction.response.send_message(
                f"✅ Mention style set to **{mention_style}** for War #{war_id}",
                ephemeral=True
            )

    # ========== /war theater & /war subhp - Theater & Sub-HP Management ==========

    # ========== THEATER COMMAND ==========

    @app_commands.command(
        name="theater",
        description="🗺️ Manage custom war theaters - Add fronts, track progress (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        war_id="War ID (autocomplete shows active wars)",
        action="What to do: Add new theater, Remove, Close (capture), Reopen, Rename, or List all",
        name="Theater name (e.g., 'Pennsylvania', 'Gulf Theater') - for Add/Rename",
        max_value="Max HP for this theater (how much warbar it represents) - for Add",
        theater_id="Which theater to modify (autocomplete shows theaters) - for Remove/Close/Reopen/Rename",
        side="Which side captured this theater - for Close only",
        new_name="New name for theater - for Rename only"
    )
    async def war_theater(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["Add", "Remove", "Close", "Reopen", "Rename", "List"],
        name: Optional[str] = None,
        max_value: Optional[int] = None,
        theater_id: Optional[int] = None,
        side: Optional[Literal["Attacker", "Defender"]] = None,
        new_name: Optional[str] = None,
    ) -> None:
        """Manage custom theaters for tracking multiple war fronts."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🗺️ Theater Management: War #{war_id}",
            description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
            color=discord.Color.blue()
        )

        # === ADD THEATER ===
        if action == "Add":
            if not name or not max_value:
                await interaction.response.send_message(
                    "❌ `name` and `max_value` required for Add action!",
                    ephemeral=True
                )
                return

            if max_value <= 0:
                await interaction.response.send_message(
                    "❌ `max_value` must be greater than 0!",
                    ephemeral=True
                )
                return

            theater_id = add_theater(war, name, max_value)
            self._save(wars)

            embed.add_field(
                name="✅ Theater Added",
                value=f"**{name}** (ID: {theater_id})\nMax HP: {max_value}",
                inline=False
            )

            embed.add_field(
                name="📊 Status",
                value="Theater starts at neutral (0). Use `/war battle` to apply damage to specific theaters.",
                inline=False
            )

        # === REMOVE THEATER ===
        elif action == "Remove":
            if theater_id is None:
                await interaction.response.send_message(
                    "❌ `theater_id` required for Remove action!",
                    ephemeral=True
                )
                return

            removed = remove_theater(war, theater_id)
            if not removed:
                await interaction.response.send_message(
                    f"❌ Theater ID {theater_id} not found!",
                    ephemeral=True
                )
                return

            self._save(wars)

            embed.add_field(
                name="🗑️ Theater Removed",
                value=f"**{removed.get('name')}** (ID: {theater_id})\nHP: {removed.get('current_value', 0)}/{removed.get('max_value', 0)}",
                inline=False
            )

            embed.add_field(
                name="ℹ️ Note",
                value="Theater HP has been added back to unassigned warbar.",
                inline=False
            )

        # === CLOSE THEATER ===
        elif action == "Close":
            if theater_id is None or not side:
                await interaction.response.send_message(
                    "❌ `theater_id` and `side` required for Close action!",
                    ephemeral=True
                )
                return

            theater = find_theater_by_id(war, theater_id)
            if not theater:
                await interaction.response.send_message(
                    f"❌ Theater ID {theater_id} not found!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            success = close_theater(war, theater_id, side_key)

            if success:
                self._save(wars)

                icon = "⚔️" if side_key == "attacker" else "🛡️"
                embed.add_field(
                    name=f"🏁 Theater Closed - {side} Victory!",
                    value=f"{icon} **{theater.get('name')}** has been captured by {side}.",
                    inline=False
                )

                embed.add_field(
                    name="📋 Next Steps",
                    value=f"• Theater is locked and no longer receives damage\n• Use `/war theater action:Reopen` to reopen if needed\n• Captured theaters may provide bonuses (future feature)",
                    inline=False
                )

        # === REOPEN THEATER ===
        elif action == "Reopen":
            if theater_id is None:
                await interaction.response.send_message(
                    "❌ `theater_id` required for Reopen action!",
                    ephemeral=True
                )
                return

            theater = find_theater_by_id(war, theater_id)
            if not theater:
                await interaction.response.send_message(
                    f"❌ Theater ID {theater_id} not found!",
                    ephemeral=True
                )
                return

            success = reopen_theater(war, theater_id)

            if success:
                self._save(wars)

                embed.add_field(
                    name="🔓 Theater Reopened",
                    value=f"**{theater.get('name')}** is now active again.\nReset to neutral (0 HP).",
                    inline=False
                )

        # === RENAME THEATER ===
        elif action == "Rename":
            if theater_id is None or not new_name:
                await interaction.response.send_message(
                    "❌ `theater_id` and `new_name` required for Rename action!",
                    ephemeral=True
                )
                return

            theater = find_theater_by_id(war, theater_id)
            if not theater:
                await interaction.response.send_message(
                    f"❌ Theater ID {theater_id} not found!",
                    ephemeral=True
                )
                return

            old_name = theater.get("name")
            theater["name"] = new_name
            self._save(wars)

            embed.add_field(
                name="✏️ Theater Renamed",
                value=f"**{old_name}** → **{new_name}**",
                inline=False
            )

        # === LIST THEATERS ===
        elif action == "List":
            theaters = war.get("theaters", [])
            unassigned = war.get("theater_unassigned", war.get("warbar", 0))

            if not theaters:
                embed.add_field(
                    name="📋 No Theaters",
                    value="No custom theaters configured for this war.\nUse `/war theater action:Add` to create theaters.",
                    inline=False
                )
            else:
                theater_lines = []
                for t in theaters:
                    tid = t.get("id")
                    tname = t.get("name")
                    current = t.get("current_value", 0)
                    max_val = t.get("max_value", 0)
                    status = t.get("status", "active")
                    captured = t.get("side_captured")

                    # Render mini progress bar
                    bar = self._render_mini_bar(current, max_val)

                    if status == "closed":
                        icon = "⚔️" if captured == "attacker" else "🛡️"
                        theater_lines.append(f"{icon} **ID {tid}: {tname}** (CLOSED - {captured} victory)")
                    else:
                        theater_lines.append(f"🗺️ **ID {tid}: {tname}** {bar} ({current:+d}/{max_val})")

                embed.add_field(
                    name="🗺️ Active Theaters",
                    value="\n".join(theater_lines),
                    inline=False
                )

            embed.add_field(
                name="📊 Unassigned Warbar",
                value=f"{unassigned:+d} (general war progress not assigned to specific theaters)",
                inline=False
            )

            total_warbar = war.get("warbar", 0)
            embed.add_field(
                name="📈 Total Warbar",
                value=f"{total_warbar:+d}/{war.get('max_value', 100)}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ========== SUB-HP COMMAND ==========

    @app_commands.command(
        name="subhp",
        description="⚡ Manage sub-healthbars - Track fleets, armies, squads in Attrition Mode (GM only)"
    )
    @app_commands.guild_only()
    @app_commands.describe(
        war_id="War ID (autocomplete shows active wars)",
        action="What to do: Add unit, Remove, Damage, Heal, Rename, or List all",
        side="Which side (Attacker or Defender)",
        name="Unit name (e.g., '1st Fleet', 'Alpha Squad', 'Northern Army') - for Add",
        max_hp="Max HP for this unit - for Add",
        subhp_id="Which unit to modify (autocomplete shows units) - for Remove/Damage/Heal/Rename",
        amount="Damage or heal amount - for Damage/Heal",
        new_name="New name for unit - for Rename only"
    )
    async def war_subhp(
        self,
        interaction: discord.Interaction,
        war_id: int,
        action: Literal["Add", "Remove", "Damage", "Heal", "Rename", "List"],
        side: Optional[Literal["Attacker", "Defender"]] = None,
        name: Optional[str] = None,
        max_hp: Optional[int] = None,
        subhp_id: Optional[int] = None,
        amount: Optional[int] = None,
        new_name: Optional[str] = None,
    ) -> None:
        """Manage sub-healthbars for tracking individual units in Attrition Mode."""
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"❌ War with ID {war_id} not found!", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"⚡ Sub-HP Management: War #{war_id}",
            description=f"**{war.get('attacker', 'Attacker')}** vs **{war.get('defender', 'Defender')}**",
            color=discord.Color.gold()
        )

        # === ADD SUB-HP ===
        if action == "Add":
            if not side or not name or not max_hp:
                await interaction.response.send_message(
                    "❌ `side`, `name`, and `max_hp` required for Add action!",
                    ephemeral=True
                )
                return

            if max_hp <= 0:
                await interaction.response.send_message(
                    "❌ `max_hp` must be greater than 0!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            subhp_id = add_subhp(war, side_key, name, max_hp)
            self._save(wars)

            embed.add_field(
                name=f"✅ Sub-HP Added: {side} Side",
                value=f"**{name}** (ID: {subhp_id})\nMax HP: {max_hp}",
                inline=False
            )

            embed.add_field(
                name="📊 Status",
                value="Unit starts at full health. Use damage/heal actions to modify.",
                inline=False
            )

        # === REMOVE SUB-HP ===
        elif action == "Remove":
            if not side or subhp_id is None:
                await interaction.response.send_message(
                    "❌ `side` and `subhp_id` required for Remove action!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            removed = remove_subhp(war, side_key, subhp_id)
            if not removed:
                await interaction.response.send_message(
                    f"❌ Sub-HP ID {subhp_id} not found on {side} side!",
                    ephemeral=True
                )
                return

            self._save(wars)

            embed.add_field(
                name=f"🗑️ Sub-HP Removed: {side} Side",
                value=f"**{removed.get('name')}** (ID: {subhp_id})\nHP: {removed.get('current_hp', 0)}/{removed.get('max_hp', 0)}",
                inline=False
            )

        # === DAMAGE SUB-HP ===
        elif action == "Damage":
            if not side or subhp_id is None or amount is None:
                await interaction.response.send_message(
                    "❌ `side`, `subhp_id`, and `amount` required for Damage action!",
                    ephemeral=True
                )
                return

            if amount <= 0:
                await interaction.response.send_message(
                    "❌ `amount` must be greater than 0!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            subhp = find_subhp_by_id(war, side_key, subhp_id)
            if not subhp:
                await interaction.response.send_message(
                    f"❌ Sub-HP ID {subhp_id} not found on {side} side!",
                    ephemeral=True
                )
                return

            old_hp = subhp.get("current_hp", 0)
            success = apply_subhp_damage(war, side_key, subhp_id, amount)

            if success:
                self._save(wars)
                new_hp = subhp.get("current_hp", 0)

                embed.add_field(
                    name=f"💥 Damage Applied: {side} Side",
                    value=f"**{subhp.get('name')}** took {amount} damage\nHP: {old_hp} → {new_hp}/{subhp.get('max_hp', 0)}",
                    inline=False
                )

                if subhp.get("status") == "neutralized":
                    embed.add_field(
                        name="☠️ Unit Neutralized",
                        value=f"**{subhp.get('name')}** has been neutralized (0 HP).\nCan be healed back into action.",
                        inline=False
                    )

        # === HEAL SUB-HP ===
        elif action == "Heal":
            if not side or subhp_id is None or amount is None:
                await interaction.response.send_message(
                    "❌ `side`, `subhp_id`, and `amount` required for Heal action!",
                    ephemeral=True
                )
                return

            if amount <= 0:
                await interaction.response.send_message(
                    "❌ `amount` must be greater than 0!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            subhp = find_subhp_by_id(war, side_key, subhp_id)
            if not subhp:
                await interaction.response.send_message(
                    f"❌ Sub-HP ID {subhp_id} not found on {side} side!",
                    ephemeral=True
                )
                return

            old_hp = subhp.get("current_hp", 0)
            old_status = subhp.get("status")
            success = apply_subhp_heal(war, side_key, subhp_id, amount)

            if success:
                self._save(wars)
                new_hp = subhp.get("current_hp", 0)

                embed.add_field(
                    name=f"💚 Heal Applied: {side} Side",
                    value=f"**{subhp.get('name')}** healed {amount} HP\nHP: {old_hp} → {new_hp}/{subhp.get('max_hp', 0)}",
                    inline=False
                )

                if old_status == "neutralized" and subhp.get("status") == "active":
                    embed.add_field(
                        name="✅ Unit Restored",
                        value=f"**{subhp.get('name')}** is back in action!",
                        inline=False
                    )

        # === RENAME SUB-HP ===
        elif action == "Rename":
            if not side or subhp_id is None or not new_name:
                await interaction.response.send_message(
                    "❌ `side`, `subhp_id`, and `new_name` required for Rename action!",
                    ephemeral=True
                )
                return

            side_key = side.lower()
            subhp = find_subhp_by_id(war, side_key, subhp_id)
            if not subhp:
                await interaction.response.send_message(
                    f"❌ Sub-HP ID {subhp_id} not found on {side} side!",
                    ephemeral=True
                )
                return

            old_name = subhp.get("name")
            subhp["name"] = new_name
            self._save(wars)

            embed.add_field(
                name=f"✏️ Sub-HP Renamed: {side} Side",
                value=f"**{old_name}** → **{new_name}**",
                inline=False
            )

        # === LIST SUB-HPS ===
        elif action == "List":
            # Attacker side
            attacker_subhps = war.get("attacker_subhps", [])
            if attacker_subhps:
                lines = []
                for s in attacker_subhps:
                    sid = s.get("id")
                    sname = s.get("name")
                    current = s.get("current_hp", 0)
                    max_val = s.get("max_hp", 0)
                    status = s.get("status", "active")

                    bar = self._render_hp_bar(current, max_val)

                    if status == "neutralized":
                        lines.append(f"☠️ **ID {sid}: {sname}** {bar} NEUTRALIZED")
                    else:
                        lines.append(f"⚡ **ID {sid}: {sname}** {bar} ({current}/{max_val} HP)")

                embed.add_field(
                    name=f"⚔️ {war.get('attacker', 'Attacker')} Units",
                    value="\n".join(lines),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"⚔️ {war.get('attacker', 'Attacker')} Units",
                    value="No sub-HPs configured",
                    inline=False
                )

            # Defender side
            defender_subhps = war.get("defender_subhps", [])
            if defender_subhps:
                lines = []
                for s in defender_subhps:
                    sid = s.get("id")
                    sname = s.get("name")
                    current = s.get("current_hp", 0)
                    max_val = s.get("max_hp", 0)
                    status = s.get("status", "active")

                    bar = self._render_hp_bar(current, max_val)

                    if status == "neutralized":
                        lines.append(f"☠️ **ID {sid}: {sname}** {bar} NEUTRALIZED")
                    else:
                        lines.append(f"⚡ **ID {sid}: {sname}** {bar} ({current}/{max_val} HP)")

                embed.add_field(
                    name=f"🛡️ {war.get('defender', 'Defender')} Units",
                    value="\n".join(lines),
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"🛡️ {war.get('defender', 'Defender')} Units",
                    value="No sub-HPs configured",
                    inline=False
                )

            # Main HP display
            attacker_hp = war.get("attacker_health", 100)
            defender_hp = war.get("defender_health", 100)
            embed.add_field(
                name="💚 Main Health",
                value=f"Attacker: {attacker_hp} | Defender: {defender_hp}",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ========== HELPER FUNCTIONS ==========

    def _render_mini_bar(self, current: int, max_value: int) -> str:
        """Render a mini progress bar for theaters."""
        if max_value == 0:
            return "[-----|-----]"

        # Normalize to -10 to +10 scale
        normalized = int((current / max_value) * 10)
        normalized = max(-10, min(10, normalized))

        if normalized == 0:
            return "[-----|-----]"
        elif normalized > 0:
            # Attacker winning
            filled = min(normalized, 5)
            return f"[{'=' * filled}{'|'}{'-' * (5 - filled)}-----]"
        else:
            # Defender winning
            filled = min(abs(normalized), 5)
            return f"[-----{'|'}{'-' * (5 - filled)}{'=' * filled}]"

    def _render_hp_bar(self, current: int, max_hp: int) -> str:
        """Render an HP bar for sub-HPs."""
        if max_hp == 0:
            return "[----------]"

        percentage = current / max_hp
        filled = int(percentage * 10)
        filled = max(0, min(10, filled))

        return f"[{'█' * filled}{'-' * (10 - filled)}]"


    # ========== /war modifier & /war npc - Modifiers & NPC Management ==========

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


# ========== Autocomplete Functions (module-level for @app_commands.autocomplete) ==========

async def _war_id_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[int]]:
    """Autocomplete for war IDs."""
    wars = load_wars()
    wars = sorted(wars, key=lambda w: w.get("id", 0), reverse=True)

    choices = []
    for war in wars[:25]:  # Discord limit
        war_id = war.get("id", 0)
        name = war.get("name", f"{war.get('attacker', '?')} vs {war.get('defender', '?')}")
        concluded = " [ENDED]" if war.get("concluded") else ""
        label = f"#{war_id}: {name}{concluded}"

        if current.lower() in label.lower() or current == str(war_id):
            choices.append(app_commands.Choice(name=label[:100], value=war_id))

    return choices


async def _modifier_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[int]]:
    """Autocomplete for modifier IDs."""
    # This is called when the user is selecting a modifier to remove
    # We'd need to know which war they're working with, but autocomplete doesn't have that context
    # For now, return empty - users will type the modifier ID manually
    return []


async def _archetype_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for NPC archetypes."""
    from ..core.npc_archetypes import NPC_ARCHETYPES

    choices = []
    for key, data in NPC_ARCHETYPES.items():
        name = data.get("name", key)
        if current.lower() in name.lower() or current.lower() in key.lower():
            choices.append(app_commands.Choice(name=name[:100], value=key))
            if len(choices) >= 25:
                break

    return choices


async def setup(bot: commands.Bot) -> None:
    """Register consolidated war commands V2."""
    await bot.add_cog(ConsolidatedWarCommandsV2(bot))
