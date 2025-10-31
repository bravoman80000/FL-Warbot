"""Theater and Sub-HP management commands.

New action-based commands for managing:
1. Custom theaters (war fronts like "Pennsylvania", "Gulf", etc.)
2. Sub-healthbars (fleets, armies, squads in Attrition Mode)
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import find_war_by_id, load_wars, save_wars
from ..core.subbar_manager import (
    add_subhp,
    add_theater,
    apply_subhp_damage,
    apply_subhp_heal,
    apply_theater_damage,
    close_theater,
    find_subhp_by_id,
    find_theater_by_id,
    remove_subhp,
    remove_theater,
    reopen_theater,
)


class TheaterSubHPCommands(commands.GroupCog, name="war"):
    """Theater and Sub-HP management commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        super().__init__()

    def _load(self) -> List[Dict[str, Any]]:
        """Load wars from data file."""
        return load_wars()

    def _save(self, wars: List[Dict[str, Any]]) -> None:
        """Save wars to data file."""
        save_wars(wars)

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


async def setup(bot: commands.Bot) -> None:
    """Register the theater and sub-HP commands."""
    await bot.add_cog(TheaterSubHPCommands(bot))
