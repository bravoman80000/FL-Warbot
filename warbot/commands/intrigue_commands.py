"""Slash commands for intrigue operations (espionage, sabotage, rebellion, etc.)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import find_war_by_id, load_wars, save_wars
from ..core.intrigue_manager import (
    apply_operation_effects,
    check_cooldown,
    create_operation,
    find_operation_by_id,
    get_active_operations_by_faction,
    get_next_operation_id,
    get_operations_by_target,
    load_operations,
    save_operations,
)
from ..core.intrigue_operations import (
    OPERATION_TYPES,
    calculate_operation_modifiers,
    get_detection_consequences,
    get_operation_impact_description,
    resolve_operation,
    roll_detection,
)


def _truncate_label(label: str, limit: int = 100) -> str:
    """Ensure Discord choice labels stay within soft limits."""
    if len(label) <= limit:
        return label
    return label[: limit - 1] + "…"


class IntrigueCommands(commands.GroupCog, name="intrigue"):
    """Commands for covert operations: espionage, sabotage, rebellion, influence."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _load_operations(self) -> List[Dict[str, Any]]:
        """Load operations from disk."""
        return load_operations()

    def _save_operations(self, operations: List[Dict[str, Any]]) -> None:
        """Save operations to disk."""
        save_operations(operations)

    def _operation_choice_results(
        self,
        interaction: discord.Interaction,
        current: str,
        *,
        statuses: Optional[Sequence[str]] = None,
        restrict_to_user: bool = False,
        prioritize_user: bool = False,
    ) -> List[app_commands.Choice[int]]:
        """Build autocomplete choices for operations."""
        operations = self._load_operations()
        statuses_lower = {status.lower() for status in statuses} if statuses else None

        filtered: List[Dict[str, Any]] = []
        for op in operations:
            status = str(op.get("status", "pending")).lower()
            if statuses_lower and status not in statuses_lower:
                continue
            if restrict_to_user and op.get("operator_member_id") != interaction.user.id:
                continue
            filtered.append(op)

        def sort_key(op: Dict[str, Any]) -> tuple[int, int]:
            own = 0
            if prioritize_user and op.get("operator_member_id") == interaction.user.id:
                own = -1
            return (own, -int(op.get("id", 0)))

        filtered.sort(key=sort_key)

        needle = current.lower()
        choices: List[app_commands.Choice[int]] = []
        for op in filtered:
            op_id = int(op.get("id", 0))
            op_type = OPERATION_TYPES.get(op.get("type", ""), {}).get("name", op.get("type", "Unknown"))
            target = op.get("target_faction") or "Unknown Target"
            status = op.get("status", "pending").title()
            label = f"#{op_id} — {op_type} vs {target} ({status})"
            if needle and needle not in label.lower():
                continue
            choices.append(app_commands.Choice(name=_truncate_label(label), value=op_id))
            if len(choices) >= 25:
                break
        return choices

    def _faction_choice_results(self, current: str) -> List[app_commands.Choice[str]]:
        """Build autocomplete choices for known faction names."""
        factions = set()
        for war in load_wars():
            factions.add(war.get("attacker"))
            factions.add(war.get("defender"))
        for op in self._load_operations():
            factions.add(op.get("operator_faction"))
            factions.add(op.get("target_faction"))

        valid_factions = sorted({f for f in factions if isinstance(f, str) and f.strip()})
        needle = current.lower()
        results: List[app_commands.Choice[str]] = []
        for faction in valid_factions:
            if needle and needle not in faction.lower():
                continue
            results.append(app_commands.Choice(name=_truncate_label(faction), value=faction))
            if len(results) >= 25:
                break
        return results

    @app_commands.command(
        name="start",
        description="Launch a covert intrigue operation.",
    )
    @app_commands.guild_only()
    @app_commands.choices(op_type=[
        app_commands.Choice(name=v["name"], value=k)
        for k, v in OPERATION_TYPES.items()
    ])
    @app_commands.choices(scale=[
        app_commands.Choice(name="Small", value="small"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Large", value="large"),
        app_commands.Choice(name="Massive", value="massive"),
    ])
    @app_commands.choices(target_strength=[
        app_commands.Choice(name="Weak", value="weak"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Strong", value="strong"),
        app_commands.Choice(name="Very Strong", value="very_strong"),
    ])
    async def intrigue_start(
        self,
        interaction: discord.Interaction,
        op_type: app_commands.Choice[str],
        operator_faction: str,
        target_faction: str,
        description: str,
        scale: app_commands.Choice[str],
        target_strength: app_commands.Choice[str],
        operator_skill: int = 0,
    ) -> None:
        """Start a new intrigue operation.

        Args:
            op_type: Type of operation (espionage, sabotage, rebellion, etc.)
            operator_faction: Your faction name
            target_faction: Target faction name
            description: Description of your operation (min 50 characters)
            scale: Operation scale (affects difficulty and impact)
            target_strength: Target faction's defensive strength
            operator_skill: Operator skill modifier (-5 to +5)
        """
        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message("This command must be used in a guild channel.", ephemeral=True)
            return

        # Validate description length
        if len(description) < 50:
            await interaction.response.send_message(
                f"❌ Description too short! Must be at least 50 characters.\n"
                f"Current length: {len(description)} characters.",
                ephemeral=True
            )
            return

        # Validate operator skill
        if not (-5 <= operator_skill <= 5):
            await interaction.response.send_message(
                "❌ Operator skill must be between -5 and +5!",
                ephemeral=True
            )
            return

        operations = self._load_operations()

        # Check cooldown
        cooldown_hours = OPERATION_TYPES[op_type.value]["cooldown_hours"]
        remaining = check_cooldown(operations, interaction.user.id, op_type.value, cooldown_hours)
        if remaining is not None:
            await interaction.response.send_message(
                f"⏳ Cooldown active for {op_type.name}. Next operation available in {remaining:.1f} hours.",
                ephemeral=True
            )
            return

        # Create operation
        operation = create_operation(
            op_type=op_type.value,
            operator_faction=operator_faction,
            target_faction=target_faction,
            operator_member_id=interaction.user.id,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            description=description,
            scale=scale.value,
            target_strength=target_strength.value,
            operator_skill=operator_skill,
        )

        # Assign ID
        operation["id"] = get_next_operation_id(operations)
        operations.append(operation)
        self._save_operations(operations)

        # Build response embed
        op_info = OPERATION_TYPES[op_type.value]
        embed = discord.Embed(
            title=f"{op_info['emoji']} Operation Initiated: {op_info['name']}",
            description=f"**Operation #{operation['id']}**",
            color=discord.Color.dark_purple()
        )

        embed.add_field(name="Operator", value=operator_faction, inline=True)
        embed.add_field(name="Target", value=target_faction, inline=True)
        embed.add_field(name="Scale", value=scale.name, inline=True)

        embed.add_field(
            name="Description",
            value=description,
            inline=False
        )

        embed.add_field(
            name="Difficulty",
            value=f"DC {operation['difficulty']} (Base: {op_info['base_dc']})",
            inline=True
        )

        embed.add_field(
            name="Detection Risk",
            value=f"{operation['detection_risk'] * 100:.0f}%",
            inline=True
        )

        embed.add_field(
            name="Cooldown",
            value=f"{cooldown_hours} hours",
            inline=True
        )

        embed.add_field(
            name="⚠️ Next Step",
            value=f"Use `/intrigue resolve op_id:{operation['id']} roll:<d20 result>` to execute!",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="resolve",
        description="Resolve an intrigue operation with your d20 roll.",
    )
    @app_commands.guild_only()
    async def intrigue_resolve(
        self,
        interaction: discord.Interaction,
        op_id: int,
        roll: int,
    ) -> None:
        """Resolve a pending intrigue operation.

        Args:
            op_id: Operation ID
            roll: Your d20 roll result (1-20)
        """
        if not (1 <= roll <= 20):
            await interaction.response.send_message(
                "❌ Roll must be between 1 and 20!",
                ephemeral=True
            )
            return

        operations = self._load_operations()
        operation = find_operation_by_id(operations, op_id)

        if operation is None:
            await interaction.response.send_message(
                f"❌ Operation #{op_id} not found!",
                ephemeral=True
            )
            return

        # Check permissions - only operator can resolve
        if operation["operator_member_id"] != interaction.user.id:
            await interaction.response.send_message(
                "❌ Only the operation initiator can resolve this operation!",
                ephemeral=True
            )
            return

        # Check status
        if operation["status"] != "pending":
            await interaction.response.send_message(
                f"❌ Operation #{op_id} has already been resolved (status: {operation['status']})!",
                ephemeral=True
            )
            return

        # Resolve operation
        status, effects = resolve_operation(operation, roll)

        # Roll for detection (unless critical success which auto-avoids detection)
        detected = False
        detection_desc = ""
        if operation["detection_risk"] > 0:
            detected, detection_desc = roll_detection(operation)

        if detected:
            status = "detected"

        # Update operation status
        operation["status"] = status
        operation["resolved_at"] = datetime.now(timezone.utc).isoformat()

        # Apply effects if successful
        impact_descriptions = []
        if status in ("success", "partial"):
            wars = load_wars()
            effect_results = apply_operation_effects(operation, wars)
            save_wars(wars)
            impact_descriptions = get_operation_impact_description(operation, status)

        # Get consequences if detected
        if detected:
            impact_descriptions = get_detection_consequences(operation)

        self._save_operations(operations)

        # Build result embed
        op_info = OPERATION_TYPES[operation["type"]]

        # Color based on outcome
        color_map = {
            "success": discord.Color.green(),
            "partial": discord.Color.gold(),
            "failure": discord.Color.orange(),
            "detected": discord.Color.red(),
        }
        color = color_map.get(status, discord.Color.greyple())

        embed = discord.Embed(
            title=f"{op_info['emoji']} Operation Resolved: {op_info['name']}",
            description=f"**Operation #{operation['id']}**",
            color=color
        )

        embed.add_field(name="Operator", value=operation["operator_faction"], inline=True)
        embed.add_field(name="Target", value=operation["target_faction"], inline=True)
        embed.add_field(name="Scale", value=operation["scale"].title(), inline=True)

        # Roll breakdown
        modifiers, total_mod = calculate_operation_modifiers(operation)
        mods_str = "\n".join(f"{name}: {val:+d}" for name, val in modifiers)
        if not mods_str:
            mods_str = "No modifiers"

        embed.add_field(
            name="🎲 Roll",
            value=f"D20: {roll}\n{mods_str}\n**Total: {operation['total']}**",
            inline=True
        )

        embed.add_field(
            name="Difficulty",
            value=f"DC {operation['difficulty']}",
            inline=True
        )

        margin = operation['total'] - operation['difficulty']
        embed.add_field(
            name="Margin",
            value=f"{margin:+d}",
            inline=True
        )

        # Outcome
        outcome_text = "\n".join(effects)
        if detected:
            outcome_text += f"\n\n{detection_desc}"

        embed.add_field(
            name="Outcome",
            value=outcome_text,
            inline=False
        )

        # Impacts
        if impact_descriptions:
            embed.add_field(
                name="Effects",
                value="\n".join(impact_descriptions),
                inline=False
            )

        await interaction.response.send_message(embed=embed)

        # Send to operation channel
        channel_id = operation.get("channel_id")
        if channel_id and channel_id != interaction.channel.id:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                if isinstance(channel, discord.abc.Messageable):
                    await channel.send(embed=embed)
            except discord.HTTPException:
                pass

    @app_commands.command(
        name="list",
        description="List active intrigue operations.",
    )
    @app_commands.guild_only()
    async def intrigue_list(
        self,
        interaction: discord.Interaction,
        faction: Optional[str] = None,
    ) -> None:
        """List intrigue operations.

        Args:
            faction: Filter by faction (operator or target). Shows all if not specified.
        """
        operations = self._load_operations()

        if faction:
            # Filter by faction
            ops_list = get_active_operations_by_faction(operations, faction)
            title = f"Active Operations: {faction}"
        else:
            # Show all active
            ops_list = [op for op in operations if op.get("status") in ("pending", "active")]
            title = "All Active Operations"

        if not ops_list:
            await interaction.response.send_message(
                "No active operations found.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=title,
            color=discord.Color.dark_purple()
        )

        for op in ops_list[:25]:  # Limit to 25 for embed field limits
            op_info = OPERATION_TYPES.get(op["type"], {})
            emoji = op_info.get("emoji", "❓")
            name = op_info.get("name", op["type"])

            status_emoji = {
                "pending": "⏳",
                "active": "🔄",
            }.get(op.get("status", "pending"), "❓")

            embed.add_field(
                name=f"{emoji} #{op['id']} — {name}",
                value=(
                    f"{status_emoji} {op['status'].title()}\n"
                    f"**Operator:** {op['operator_faction']}\n"
                    f"**Target:** {op['target_faction']}\n"
                    f"**Scale:** {op.get('scale', 'unknown').title()}\n"
                    f"**DC:** {op['difficulty']} | **Detection:** {op['detection_risk'] * 100:.0f}%"
                ),
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="status",
        description="View details of a specific intrigue operation.",
    )
    @app_commands.guild_only()
    async def intrigue_status(
        self,
        interaction: discord.Interaction,
        op_id: int,
    ) -> None:
        """View operation details.

        Args:
            op_id: Operation ID to view
        """
        operations = self._load_operations()
        operation = find_operation_by_id(operations, op_id)

        if operation is None:
            await interaction.response.send_message(
                f"❌ Operation #{op_id} not found!",
                ephemeral=True
            )
            return

        op_info = OPERATION_TYPES.get(operation["type"], {})

        # Color based on status
        color_map = {
            "pending": discord.Color.yellow(),
            "active": discord.Color.blue(),
            "success": discord.Color.green(),
            "partial": discord.Color.gold(),
            "failure": discord.Color.orange(),
            "detected": discord.Color.red(),
            "cancelled": discord.Color.greyple(),
        }
        color = color_map.get(operation.get("status", "pending"), discord.Color.greyple())

        embed = discord.Embed(
            title=f"{op_info.get('emoji', '❓')} Operation #{op_id}: {op_info.get('name', operation['type'])}",
            description=operation.get("description", "No description"),
            color=color
        )

        embed.add_field(name="Status", value=operation["status"].title(), inline=True)
        embed.add_field(name="Operator", value=operation["operator_faction"], inline=True)
        embed.add_field(name="Target", value=operation["target_faction"], inline=True)

        embed.add_field(name="Scale", value=operation.get("scale", "unknown").title(), inline=True)
        embed.add_field(name="Difficulty", value=f"DC {operation['difficulty']}", inline=True)
        embed.add_field(name="Detection Risk", value=f"{operation['detection_risk'] * 100:.0f}%", inline=True)

        # If resolved, show results
        if operation.get("roll") is not None:
            modifiers, total_mod = calculate_operation_modifiers(operation)
            mods_str = "\n".join(f"{name}: {val:+d}" for name, val in modifiers)
            if not mods_str:
                mods_str = "No modifiers"

            embed.add_field(
                name="Roll Result",
                value=f"D20: {operation['roll']}\n{mods_str}\n**Total: {operation['total']}**",
                inline=False
            )

        if operation.get("detected_by"):
            embed.add_field(
                name="⚠️ Detected By",
                value=operation["detected_by"],
                inline=True
            )

        # Timestamps
        created = operation.get("created_at", "Unknown")
        embed.add_field(name="Created", value=created[:19], inline=True)

        if operation.get("resolved_at"):
            resolved = operation["resolved_at"][:19]
            embed.add_field(name="Resolved", value=resolved, inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="sabotage",
        description="Launch a sabotage operation targeting specific infrastructure.",
    )
    @app_commands.guild_only()
    @app_commands.choices(target_category=[
        app_commands.Choice(name="Military (Ground Forces)", value="military"),
        app_commands.Choice(name="Naval (Sea/Water Forces)", value="naval"),
        app_commands.Choice(name="Exosphere (Space/Air Forces)", value="exosphere"),
    ])
    @app_commands.choices(scale=[
        app_commands.Choice(name="Small", value="small"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Large", value="large"),
        app_commands.Choice(name="Massive", value="massive"),
    ])
    @app_commands.choices(target_strength=[
        app_commands.Choice(name="Weak", value="weak"),
        app_commands.Choice(name="Medium", value="medium"),
        app_commands.Choice(name="Strong", value="strong"),
        app_commands.Choice(name="Very Strong", value="very_strong"),
    ])
    async def intrigue_sabotage(
        self,
        interaction: discord.Interaction,
        operator_faction: str,
        target_faction: str,
        target_category: app_commands.Choice[str],
        description: str,
        scale: app_commands.Choice[str],
        target_strength: app_commands.Choice[str],
        operator_skill: int = 0,
    ) -> None:
        """Sabotage operation with specific infrastructure targeting.

        This is a specialized version of `/intrigue start` for sabotage operations.
        """
        # Reuse the main start logic but with sabotage-specific defaults
        op_choice = app_commands.Choice(name="Sabotage", value="sabotage")

        if not interaction.guild or not interaction.channel:
            await interaction.response.send_message("This command must be used in a guild channel.", ephemeral=True)
            return

        if len(description) < 50:
            await interaction.response.send_message(
                f"❌ Description too short! Must be at least 50 characters.\nCurrent length: {len(description)} characters.",
                ephemeral=True
            )
            return

        if not (-5 <= operator_skill <= 5):
            await interaction.response.send_message("❌ Operator skill must be between -5 and +5!", ephemeral=True)
            return

        operations = self._load_operations()

        cooldown_hours = OPERATION_TYPES["sabotage"]["cooldown_hours"]
        remaining = check_cooldown(operations, interaction.user.id, "sabotage", cooldown_hours)
        if remaining is not None:
            await interaction.response.send_message(
                f"⏳ Cooldown active for Sabotage. Next operation available in {remaining:.1f} hours.",
                ephemeral=True
            )
            return

        # Create sabotage operation with target_category
        operation = create_operation(
            op_type="sabotage",
            operator_faction=operator_faction,
            target_faction=target_faction,
            operator_member_id=interaction.user.id,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            description=description,
            scale=scale.value,
            target_strength=target_strength.value,
            operator_skill=operator_skill,
            target_category=target_category.value,  # Sabotage-specific
        )

        operation["id"] = get_next_operation_id(operations)
        operations.append(operation)
        self._save_operations(operations)

        op_info = OPERATION_TYPES["sabotage"]
        embed = discord.Embed(
            title=f"{op_info['emoji']} Sabotage Operation Initiated",
            description=f"**Operation #{operation['id']}**",
            color=discord.Color.dark_red()
        )

        embed.add_field(name="Operator", value=operator_faction, inline=True)
        embed.add_field(name="Target", value=target_faction, inline=True)
        embed.add_field(name="Target Category", value=target_category.name, inline=True)
        embed.add_field(name="Scale", value=scale.name, inline=True)

        embed.add_field(name="Description", value=description, inline=False)

        embed.add_field(name="Difficulty", value=f"DC {operation['difficulty']}", inline=True)
        embed.add_field(name="Detection Risk", value=f"{operation['detection_risk'] * 100:.0f}%", inline=True)
        embed.add_field(name="Cooldown", value=f"{cooldown_hours} hours", inline=True)

        embed.add_field(
            name="⚠️ Next Step",
            value=f"Use `/intrigue resolve op_id:{operation['id']} roll:<d20 result>` to execute!",
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="cancel",
        description="Cancel a pending intrigue operation.",
    )
    @app_commands.guild_only()
    async def intrigue_cancel(
        self,
        interaction: discord.Interaction,
        op_id: int,
    ) -> None:
        """Cancel a pending operation.

        Args:
            op_id: Operation ID to cancel
        """
        operations = self._load_operations()
        operation = find_operation_by_id(operations, op_id)

        if operation is None:
            await interaction.response.send_message(
                f"❌ Operation #{op_id} not found!",
                ephemeral=True
            )
            return

        # Check permissions
        if operation["operator_member_id"] != interaction.user.id:
            # Check if user has admin/GM role (you might want to customize this)
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ Only the operator or an administrator can cancel this operation!",
                    ephemeral=True
                )
                return

        # Check status
        if operation["status"] != "pending":
            await interaction.response.send_message(
                f"❌ Cannot cancel operation #{op_id} (status: {operation['status']})!",
                ephemeral=True
            )
            return

        operation["status"] = "cancelled"
        operation["resolved_at"] = datetime.now(timezone.utc).isoformat()
        self._save_operations(operations)

        await interaction.response.send_message(
            f"✅ Operation #{op_id} cancelled.",
            ephemeral=True
        )

    @app_commands.command(
        name="intel",
        description="View intelligence gathered from successful espionage operations.",
    )
    @app_commands.guild_only()
    async def intrigue_intel(
        self,
        interaction: discord.Interaction,
        target_faction: str,
    ) -> None:
        """View intelligence on a faction gathered from espionage.

        Args:
            target_faction: Faction to view intelligence on
        """
        operations = self._load_operations()

        # Find successful espionage operations against this faction
        espionage_ops = [
            op for op in operations
            if op.get("type") == "espionage"
            and op.get("target_faction") == target_faction
            and op.get("status") == "success"
            and op.get("operator_member_id") == interaction.user.id  # Only show user's own intel
        ]

        if not espionage_ops:
            await interaction.response.send_message(
                f"❌ No intelligence available on {target_faction}.\nLaunch espionage operations to gather intel!",
                ephemeral=True
            )
            return

        # Load wars to show target's war status
        wars = load_wars()
        target_wars = [
            war for war in wars
            if war.get("attacker") == target_faction or war.get("defender") == target_faction
        ]

        embed = discord.Embed(
            title=f"🕵️ Intelligence Dossier: {target_faction}",
            description=f"Based on {len(espionage_ops)} successful espionage operation(s)",
            color=discord.Color.dark_blue()
        )

        # Show faction stats from most recent espionage
        if target_wars:
            latest_war = target_wars[0]
            side = "attacker" if latest_war.get("attacker") == target_faction else "defender"
            stats = latest_war.get("stats", {}).get(side, {})

            embed.add_field(
                name="📊 Military Capabilities",
                value=(
                    f"Exosphere: {stats.get('exosphere', '?')}\n"
                    f"Naval: {stats.get('naval', '?')}\n"
                    f"Military: {stats.get('military', '?')}"
                ),
                inline=True
            )

        # Show active wars
        if target_wars:
            wars_list = "\n".join(
                f"#{war['id']}: {war.get('attacker', '?')} vs {war.get('defender', '?')}"
                for war in target_wars[:5]
            )
            embed.add_field(
                name="⚔️ Active Wars",
                value=wars_list or "None",
                inline=True
            )

        # Show detected intrigue operations by target faction
        target_ops = get_operations_by_target(operations, target_faction, status="active")
        if target_ops:
            ops_list = "\n".join(
                f"Op #{op['id']}: {op['type'].title()} ({op.get('scale', '?')} scale)"
                for op in target_ops[:5]
            )
            embed.add_field(
                name="🎯 Ongoing Operations Against Them",
                value=ops_list,
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(
        name="alerts",
        description="View detected enemy intrigue operations targeting your faction.",
    )
    @app_commands.guild_only()
    async def intrigue_alerts(
        self,
        interaction: discord.Interaction,
        faction: str,
    ) -> None:
        """View detected enemy operations targeting your faction.

        Args:
            faction: Your faction name
        """
        operations = self._load_operations()

        # Find detected operations targeting this faction
        detected_ops = [
            op for op in operations
            if op.get("target_faction") == faction
            and op.get("status") == "detected"
        ]

        if not detected_ops:
            await interaction.response.send_message(
                f"✅ No detected enemy operations against {faction}.",
                ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"🚨 Intrigue Alerts: {faction}",
            description=f"{len(detected_ops)} enemy operation(s) detected",
            color=discord.Color.red()
        )

        for op in detected_ops[:10]:  # Limit to 10
            op_info = OPERATION_TYPES.get(op["type"], {})
            emoji = op_info.get("emoji", "❓")

            embed.add_field(
                name=f"{emoji} Op #{op['id']}: {op_info.get('name', op['type'])}",
                value=(
                    f"**Operator:** {op.get('operator_faction', 'Unknown')}\n"
                    f"**Scale:** {op.get('scale', 'unknown').title()}\n"
                    f"**Status:** {op['status'].title()}\n"
                    f"**Detected:** {op.get('resolved_at', 'Unknown')[:19]}"
                ),
                inline=True
            )

        await interaction.response.send_message(embed=embed)

    # === AUTOCOMPLETE PROVIDERS ===

    @intrigue_start.autocomplete("operator_faction")
    async def intrigue_start_operator_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return self._faction_choice_results(current)

    @intrigue_start.autocomplete("target_faction")
    async def intrigue_start_target_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return self._faction_choice_results(current)

    @intrigue_sabotage.autocomplete("operator_faction")
    async def intrigue_sabotage_operator_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return self._faction_choice_results(current)

    @intrigue_sabotage.autocomplete("target_faction")
    async def intrigue_sabotage_target_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return self._faction_choice_results(current)

    @intrigue_list.autocomplete("faction")
    async def intrigue_list_faction_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return self._faction_choice_results(current)

    @intrigue_intel.autocomplete("target_faction")
    async def intrigue_intel_target_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return self._faction_choice_results(current)

    @intrigue_alerts.autocomplete("faction")
    async def intrigue_alerts_faction_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[str]]:
        return self._faction_choice_results(current)

    @intrigue_resolve.autocomplete("op_id")
    async def intrigue_resolve_op_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._operation_choice_results(
            interaction,
            current,
            statuses=("pending",),
            restrict_to_user=True,
        )

    @intrigue_status.autocomplete("op_id")
    async def intrigue_status_op_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._operation_choice_results(interaction, current)

    @intrigue_cancel.autocomplete("op_id")
    async def intrigue_cancel_op_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._operation_choice_results(
            interaction,
            current,
            statuses=("pending",),
            prioritize_user=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(IntrigueCommands(bot))
