"""Fully consolidated war commands - OPERATION GREENLIGHT 2.0

All war commands restructured into clean action-based groups:
- /war manage - Create, End, Status wars
- /war battle - Resolve, Next turn
- /war roster - Add, Remove, List players
- /war settings - Mode, Name, Channel, Mention
- /war action - THE PLAYER COMMAND (standalone)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import find_war_by_id, load_wars, save_wars, apply_war_defaults

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


async def setup(bot: commands.Bot) -> None:
    """Register consolidated war commands V2."""
    await bot.add_cog(ConsolidatedWarCommandsV2(bot))
