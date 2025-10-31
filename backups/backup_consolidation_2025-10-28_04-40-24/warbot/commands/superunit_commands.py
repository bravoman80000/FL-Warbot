"""Slash commands for Super Unit management."""

from __future__ import annotations

from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import load_wars
from ..core.superunit_manager import (
    calculate_combat_modifier,
    find_super_unit_by_id,
    load_super_units,
    save_super_units,
)


def _truncate_label(label: str, limit: int = 100) -> str:
    """Limit Discord choice labels to the desired length."""
    if len(label) <= limit:
        return label
    return label[: limit - 1] + "…"


class SuperUnitCommands(commands.GroupCog, name="superunit"):
    """Cog implementing `/superunit` command group."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    def _load(self) -> List[dict]:
        return load_super_units()

    def _save(self, units: List[dict]) -> None:
        save_super_units(units)

    def _next_unit_id(self, units: List[dict]) -> int:
        if not units:
            return 1
        return max(int(unit.get("id", 0)) for unit in units) + 1

    def _unit_choice_results(self, current: str) -> List[app_commands.Choice[int]]:
        """Return matching super unit choices for autocomplete inputs."""
        units = sorted(self._load(), key=lambda unit: int(unit.get("id", 0)))
        current_lower = current.lower()
        choices: List[app_commands.Choice[int]] = []
        for unit in units:
            unit_id = int(unit.get("id", 0))
            name = unit.get("name") or f"Super Unit #{unit_id}"
            war_id = unit.get("war_id")
            status = unit.get("status", "active").title()
            suffix = f" • War #{war_id}" if war_id else ""
            label = f"#{unit_id} — {name} [{status}]{suffix}"
            if current_lower and current_lower not in label.lower():
                continue
            choices.append(app_commands.Choice(name=_truncate_label(label), value=unit_id))
            if len(choices) >= 25:
                break
        return choices

    def _war_choice_results(self, current: str) -> List[app_commands.Choice[int]]:
        """Return matching war choices for optional super unit linking."""
        wars = sorted(load_wars(), key=lambda war: int(war.get("id", 0)))
        current_lower = current.lower()
        results: List[app_commands.Choice[int]] = []
        for war in wars:
            war_id = int(war.get("id", 0))
            name = war.get("name") or f"{war.get('attacker', 'Unknown')} vs {war.get('defender', 'Unknown')}"
            label = f"#{war_id} — {name}"
            if current_lower and current_lower not in label.lower():
                continue
            results.append(app_commands.Choice(name=_truncate_label(label), value=war_id))
            if len(results) >= 25:
                break
        return results

    # === COMMAND: /superunit create ===
    @app_commands.command(
        name="create",
        description="Create a new Super Unit to track.",
    )
    @app_commands.guild_only()
    async def superunit_create(
        self,
        interaction: discord.Interaction,
        name: str,
        max_intel: int,
        description: str,
        war_id: Optional[int] = None,
    ) -> None:
        units = self._load()

        unit = {
            "id": self._next_unit_id(units),
            "name": name,
            "description": description,
            "max_intel": max_intel,
            "current_intel": 0,
            "intel_descriptions": ["[Locked]" for _ in range(max_intel)],
            "research_log": [],
            "war_id": war_id,
            "health": 100,
            "max_health": 100,
            "status": "active",
        }

        units.append(unit)
        self._save(units)

        embed = discord.Embed(
            title=f"🛡️ Super Unit Created",
            description=f"**{name}**\n{description}",
            color=discord.Color.purple(),
        )
        embed.add_field(name="Unit ID", value=str(unit["id"]), inline=True)
        embed.add_field(name="Max Intel", value=f"{max_intel} pieces", inline=True)
        if war_id:
            embed.add_field(name="Linked War", value=f"War #{war_id}", inline=True)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === COMMAND: /superunit set_intel ===
    @app_commands.command(
        name="set_intel",
        description="Set the description for a specific intel slot.",
    )
    @app_commands.guild_only()
    async def superunit_set_intel(
        self,
        interaction: discord.Interaction,
        unit_id: int,
        intel_slot: int,
        description: str,
    ) -> None:
        units = self._load()
        unit = find_super_unit_by_id(units, unit_id)
        if unit is None:
            await interaction.response.send_message(
                f"Super Unit with ID {unit_id} not found.", ephemeral=True
            )
            return

        if not (1 <= intel_slot <= unit["max_intel"]):
            await interaction.response.send_message(
                f"Intel slot must be between 1 and {unit['max_intel']}.", ephemeral=True
            )
            return

        unit["intel_descriptions"][intel_slot - 1] = description
        self._save(units)

        await interaction.response.send_message(
            f"✅ Intel slot {intel_slot} set for **{unit['name']}**:\n{description}",
            ephemeral=True,
        )

    # === COMMAND: /superunit research ===
    @app_commands.command(
        name="research",
        description="Record a research attempt on a Super Unit.",
    )
    @app_commands.guild_only()
    async def superunit_research(
        self,
        interaction: discord.Interaction,
        unit_id: int,
        researcher: discord.Member,
        roll: int,
    ) -> None:
        units = self._load()
        unit = find_super_unit_by_id(units, unit_id)
        if unit is None:
            await interaction.response.send_message(
                f"Super Unit with ID {unit_id} not found.", ephemeral=True
            )
            return

        # Determine success
        success = roll == 20 or roll >= 15

        # Log research attempt
        unit["research_log"].append({
            "researcher_id": researcher.id,
            "researcher_name": researcher.display_name,
            "roll": roll,
            "success": success,
        })

        # Grant intel if successful
        if success and unit["current_intel"] < unit["max_intel"]:
            unit["current_intel"] += 1
            intel_unlocked = unit["current_intel"]
            intel_text = unit["intel_descriptions"][intel_unlocked - 1]

            self._save(units)

            embed = discord.Embed(
                title="🔬 Research Successful!",
                description=f"**{researcher.display_name}** unlocked intel on **{unit['name']}**!",
                color=discord.Color.green(),
            )
            embed.add_field(
                name=f"Intel {intel_unlocked}/{unit['max_intel']} Unlocked",
                value=intel_text,
                inline=False,
            )
            embed.add_field(name="Roll", value=str(roll), inline=True)
            embed.add_field(
                name="Combat Modifier",
                value=f"{calculate_combat_modifier(unit):+d}",
                inline=True,
            )

            await interaction.response.send_message(embed=embed)
        else:
            self._save(units)

            await interaction.response.send_message(
                f"🔬 Research attempt by {researcher.display_name} (roll: {roll}) - **No new intel gained.**",
                ephemeral=True,
            )

    # === COMMAND: /superunit grant_intel ===
    @app_commands.command(
        name="grant_intel",
        description="GM manually grants intel (bypasses research rolls).",
    )
    @app_commands.guild_only()
    async def superunit_grant_intel(
        self,
        interaction: discord.Interaction,
        unit_id: int,
        intel_slot: int,
        reason: str = "GM granted",
    ) -> None:
        units = self._load()
        unit = find_super_unit_by_id(units, unit_id)
        if unit is None:
            await interaction.response.send_message(
                f"Super Unit with ID {unit_id} not found.", ephemeral=True
            )
            return

        if not (1 <= intel_slot <= unit["max_intel"]):
            await interaction.response.send_message(
                f"Intel slot must be between 1 and {unit['max_intel']}.", ephemeral=True
            )
            return

        if intel_slot <= unit["current_intel"]:
            await interaction.response.send_message(
                f"Intel slot {intel_slot} is already unlocked!", ephemeral=True
            )
            return

        # Unlock up to this intel slot
        unit["current_intel"] = intel_slot
        intel_text = unit["intel_descriptions"][intel_slot - 1]

        # Log as GM grant
        unit["research_log"].append({
            "researcher_id": interaction.user.id,
            "researcher_name": "GM",
            "roll": None,
            "success": True,
            "reason": reason,
        })

        self._save(units)

        embed = discord.Embed(
            title="🔓 Intel Granted",
            description=f"Intel {intel_slot}/{unit['max_intel']} unlocked for **{unit['name']}**",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Intel", value=intel_text, inline=False)
        embed.add_field(name="Reason", value=reason, inline=True)
        embed.add_field(
            name="Combat Modifier",
            value=f"{calculate_combat_modifier(unit):+d}",
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === COMMAND: /superunit status ===
    @app_commands.command(
        name="status",
        description="Show Super Unit status and intel progress.",
    )
    @app_commands.guild_only()
    async def superunit_status(
        self,
        interaction: discord.Interaction,
        unit_id: int,
    ) -> None:
        units = self._load()
        unit = find_super_unit_by_id(units, unit_id)
        if unit is None:
            await interaction.response.send_message(
                f"Super Unit with ID {unit_id} not found.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🛡️ {unit['name']}",
            description=unit.get("description", "No description"),
            color=discord.Color.purple(),
        )

        # Intel progress
        progress_bar = "".join(
            ["✅" if i < unit["current_intel"] else "🔒" for i in range(unit["max_intel"])]
        )
        embed.add_field(
            name="Intel Progress",
            value=f"{progress_bar}\n{unit['current_intel']}/{unit['max_intel']} unlocked",
            inline=False,
        )

        # Show unlocked intel
        for i in range(unit["current_intel"]):
            embed.add_field(
                name=f"Intel {i+1}",
                value=unit["intel_descriptions"][i],
                inline=False,
            )

        # Combat modifier
        modifier = calculate_combat_modifier(unit)
        embed.add_field(
            name="Combat Modifier",
            value=f"{modifier:+d}",
            inline=True,
        )

        # Status
        embed.add_field(name="Status", value=unit.get("status", "active").title(), inline=True)

        # Health (for flashpoint combat)
        health = unit.get("health", 100)
        max_health = unit.get("max_health", 100)
        embed.add_field(
            name="Health",
            value=f"{health}/{max_health}",
            inline=True,
        )

        # Research log count
        embed.add_field(
            name="Research Attempts",
            value=str(len(unit.get("research_log", []))),
            inline=True,
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === AUTOCOMPLETE PROVIDERS ===

    @superunit_create.autocomplete("war_id")
    async def superunit_create_war_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @superunit_set_intel.autocomplete("unit_id")
    async def superunit_set_intel_unit_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._unit_choice_results(current)

    @superunit_research.autocomplete("unit_id")
    async def superunit_research_unit_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._unit_choice_results(current)

    @superunit_grant_intel.autocomplete("unit_id")
    async def superunit_grant_intel_unit_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._unit_choice_results(current)

    @superunit_status.autocomplete("unit_id")
    async def superunit_status_unit_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._unit_choice_results(current)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SuperUnitCommands(bot))
