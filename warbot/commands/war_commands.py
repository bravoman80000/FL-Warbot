"""Slash commands for managing wars."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import find_war_by_id, load_wars, save_wars
from ..core.utils import calculate_momentum, clamp, render_warbar, update_timestamp


def _derive_last_winner(momentum: int) -> Optional[str]:
    """Infer the last winning side from the stored momentum value."""
    if momentum > 0:
        return "attacker"
    if momentum < 0:
        return "defender"
    return None


def _flip_initiative(current: str) -> str:
    """Flip initiative between attacker and defender."""
    return "defender" if current == "attacker" else "attacker"


def _format_momentum(momentum: int) -> str:
    """Render momentum with sign for embeds."""
    prefix = "+" if momentum > 0 else ""
    return f"{prefix}{momentum}"


def _format_war_name(war: Dict[str, Any]) -> str:
    return war.get("name") or f"War #{war.get('id')}"


def _war_momentum_summary(momentum: int) -> str:
    if momentum > 0:
        return f"+{momentum} (Attacker)"
    if momentum < 0:
        return f"{momentum} (Defender)"
    return "0 (Neutral)"


def _warbar_summary(value: int) -> str:
    direction = "Neutral"
    if value > 0:
        direction = "Attacker Advantage"
    elif value < 0:
        direction = "Defender Advantage"
    return f"{render_warbar(value)}\nWarBar: {value:+d} ({direction})"


def _parse_timestamp(raw: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@dataclass(frozen=True)
class VictoryOption:
    label: str
    shift: int
    style: discord.ButtonStyle


VICTORY_OPTIONS: Sequence[VictoryOption] = (
    VictoryOption("Narrow Victory", 5, discord.ButtonStyle.secondary),
    VictoryOption("Marginal Victory", 10, discord.ButtonStyle.primary),
    VictoryOption("Clear Victory", 15, discord.ButtonStyle.success),
    VictoryOption("Decisive Victory", 20, discord.ButtonStyle.danger),
)


class WinnerButton(discord.ui.Button["WarResolutionView"]):
    def __init__(self, label: str, style: discord.ButtonStyle, winner: str) -> None:
        super().__init__(label=label, style=style)
        self.winner = winner

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.handle_winner(interaction, self.winner)


class VictoryButton(discord.ui.Button["WarResolutionView"]):
    def __init__(self, option: VictoryOption) -> None:
        super().__init__(label=option.label, style=option.style, disabled=True)
        self.option = option

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.handle_victory(interaction, self.option)


class ResolutionNotesModal(discord.ui.Modal):
    """Modal to capture optional resolution notes."""

    def __init__(self, parent_view: "WarResolutionView") -> None:
        super().__init__(title="Resolution Notes (Optional)")
        self.parent_view = parent_view
        self.notes_input = discord.ui.TextInput(
            label="Notes",
            placeholder="Strategic hooks, casualties, reminders…",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )
        self.add_item(self.notes_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.parent_view.notes = str(self.notes_input.value or "").strip()
        await interaction.response.send_message(
            "Resolution captured. Posting results…", ephemeral=True
        )
        await self.parent_view.finalise()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await interaction.response.send_message(
            f"Failed to record notes: {error}", ephemeral=True
        )
        await self.parent_view.cancel("An unexpected error occurred while saving notes.")


class WarResolutionView(discord.ui.View):
    """Interactive flow for /war resolve."""

    def __init__(self, user: discord.abc.User, war_name: str) -> None:
        super().__init__(timeout=300)
        self.user = user
        self.war_name = war_name
        self.message: Optional[discord.Message] = None
        self.winner: Optional[str] = None
        self.victory: Optional[VictoryOption] = None
        self.notes: str = ""
        self.result: Optional[Dict[str, Any]] = None
        self._finished = asyncio.Event()

        # Winner selection row
        self.add_item(WinnerButton("Attacker", discord.ButtonStyle.success, "attacker"))
        self.add_item(WinnerButton("Defender", discord.ButtonStyle.danger, "defender"))
        self.add_item(WinnerButton("Stalemate", discord.ButtonStyle.secondary, "stalemate"))

        # Victory type row
        for option in VICTORY_OPTIONS:
            self.add_item(VictoryButton(option))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "Only the command invoker can use this resolution view.",
                ephemeral=True,
            )
            return False
        return True

    async def handle_winner(self, interaction: discord.Interaction, winner: str) -> None:
        self.winner = winner
        self.disable_winner_buttons()
        if winner == "stalemate":
            self.disable_victory_buttons()
            if self.message:
                await self.message.edit(
                    content=f"Winner: **Stalemate** — proceeding to notes.",
                    view=self,
                )
            await self.prompt_notes(interaction)
            return

        self.enable_victory_buttons()
        await interaction.response.edit_message(
            content=(
                f"Winner selected: **{winner.title()}**.\n"
                "Step 2 — choose the victory type."
            ),
            view=self,
        )

    async def handle_victory(
        self, interaction: discord.Interaction, option: VictoryOption
    ) -> None:
        self.victory = option
        if self.message:
            await self.message.edit(
                content=(
                    f"Victory set to **{option.label}**.\n"
                    "Step 3 — add notes (optional)."
                ),
                view=self,
            )
        await self.prompt_notes(interaction)

    async def prompt_notes(self, interaction: discord.Interaction) -> None:
        modal = ResolutionNotesModal(self)
        await interaction.response.send_modal(modal)

    async def finalise(self) -> None:
        self.disable_all()
        if self.winner == "stalemate":
            victory_label = "Stalemate"
            shift = 0
        else:
            victory_label = self.victory.label if self.victory else "No Shift"
            shift = self.victory.shift if self.victory else 0

        if self.winner == "defender":
            net_shift = -shift
        elif self.winner == "attacker":
            net_shift = shift
        else:
            net_shift = 0

        self.result = {
            "winner": self.winner,
            "victory_label": victory_label,
            "shift": net_shift,
            "notes": self.notes,
        }

        if self.message:
            await self.message.edit(
                content=(
                    f"Resolution ready for **{self.war_name}**.\n"
                    "Posting summary to channel."
                ),
                view=self,
            )
        self.stop()
        self._finished.set()

    async def cancel(self, reason: str) -> None:
        self.disable_all()
        if self.message:
            await self.message.edit(content=reason, view=self)
        self.stop()
        self._finished.set()

    def disable_victory_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, VictoryButton):
                item.disabled = True

    def disable_winner_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, WinnerButton):
                item.disabled = True

    def enable_victory_buttons(self) -> None:
        for item in self.children:
            if isinstance(item, VictoryButton):
                item.disabled = False

    def disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self) -> None:
        await self.cancel("Resolution timed out — please run `/war resolve` again.")

    async def wait_for_result(self) -> Optional[Dict[str, Any]]:
        await self._finished.wait()
        return self.result


class WarCommands(commands.Cog):
    """Cog implementing `/war` commands."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    def _load(self) -> List[Dict[str, Any]]:
        return load_wars()

    def _save(self, wars: List[Dict[str, Any]]) -> None:
        save_wars(wars)

    def _next_war_id(self, wars: Sequence[Dict[str, Any]]) -> int:
        if not wars:
            return 1
        return max(int(war.get("id", 0)) for war in wars) + 1

    def _war_embed(self, war: Dict[str, Any], *, title: str) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=_warbar_summary(int(war.get("warbar", 0))),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="ID", value=str(war.get("id")), inline=True)
        embed.add_field(name="Theater", value=war.get("theater", "Unknown"), inline=True)
        embed.add_field(name="Mode", value=war.get("mode", "Unknown"), inline=True)
        embed.add_field(
            name="Initiative", value=war.get("initiative", "attacker").title(), inline=True
        )
        embed.add_field(
            name="Momentum", value=_war_momentum_summary(int(war.get("momentum", 0))), inline=True
        )
        embed.add_field(
            name="Last Update",
            value=war.get("last_update", "Unknown"),
            inline=True,
        )
        channel_id = war.get("channel_id")
        if channel_id:
            embed.add_field(
                name="Channel",
                value=f"<#{int(channel_id)}>",
                inline=False,
            )
        notes = war.get("notes", "").strip()
        if notes:
            embed.add_field(name="Notes", value=notes, inline=False)
        embed.set_footer(text=f"{war.get('attacker')} vs {war.get('defender')}")
        return embed

    # === COMMAND: /war start ===
    @app_commands.command(name="start", description="Start tracking a new war.")
    @app_commands.guild_only()
    async def war_start(
        self,
        interaction: discord.Interaction,
        attacker: str,
        defender: str,
        theater: str,
        mode: str,
    ) -> None:
        wars = self._load()
        war_id = self._next_war_id(wars)
        war_name = f"{attacker} vs {defender}"
        channel_id = interaction.channel_id
        war = {
            "id": war_id,
            "name": war_name,
            "attacker": attacker,
            "defender": defender,
            "theater": theater,
            "mode": mode,
            "warbar": 0,
            "momentum": 0,
            "initiative": "attacker",
            "last_update": update_timestamp(),
            "notes": "",
            "channel_id": int(channel_id) if channel_id is not None else None,
        }
        wars.append(war)
        self._save(wars)

        embed = self._war_embed(war, title=f"War Started — {war_name}")
        await interaction.response.send_message(embed=embed, allowed_mentions=discord.AllowedMentions.none())

    # === COMMAND: /war list ===
    @app_commands.command(name="list", description="List all active wars.")
    @app_commands.guild_only()
    async def war_list(self, interaction: discord.Interaction) -> None:
        wars = self._load()
        if not wars:
            await interaction.response.send_message(
                "No active wars found.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title="Active Wars",
            color=discord.Color.blurple(),
        )

        for war in wars:
            embed.add_field(
                name=f"#{war.get('id')} — {_format_war_name(war)}",
                value=(
                    f"{render_warbar(int(war.get('warbar', 0)))}\n"
                    f"Initiative: {war.get('initiative', 'attacker').title()} · "
                    f"Momentum: {_war_momentum_summary(int(war.get('momentum', 0)))}"
                ),
                inline=False,
            )
        await interaction.response.send_message(embed=embed)

    # === COMMAND: /war status ===
    @app_commands.command(name="status", description="Show war status details.")
    @app_commands.guild_only()
    async def war_status(self, interaction: discord.Interaction, war_id: Optional[int] = None) -> None:
        wars = self._load()
        if not wars:
            await interaction.response.send_message(
                "No active wars tracked.", ephemeral=True
            )
            return

        war: Optional[Dict[str, Any]] = None
        if war_id is not None:
            war = find_war_by_id(wars, war_id)
        elif len(wars) == 1:
            war = wars[0]

        if war is None:
            await interaction.response.send_message(
                "War not found. Provide a valid ID from `/war list`.",
                ephemeral=True,
            )
            return

        embed = self._war_embed(war, title=f"War Status — {_format_war_name(war)}")
        await interaction.response.send_message(embed=embed)

    # === COMMAND: /war update ===
    @app_commands.command(
        name="update",
        description="Edit war metadata such as theater, participants, or channel.",
    )
    @app_commands.guild_only()
    async def war_update(
        self,
        interaction: discord.Interaction,
        war_id: int,
        name: Optional[str] = None,
        attacker: Optional[str] = None,
        defender: Optional[str] = None,
        theater: Optional[str] = None,
        mode: Optional[str] = None,
        channel: Optional[discord.abc.GuildChannel] = None,
        thread: Optional[discord.Thread] = None,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        applied: List[str] = []
        if name:
            war["name"] = name
            applied.append("name")
        if attacker:
            war["attacker"] = attacker
            applied.append("attacker")
        if defender:
            war["defender"] = defender
            applied.append("defender")
        if theater:
            war["theater"] = theater
            applied.append("theater")
        if mode:
            war["mode"] = mode
            applied.append("mode")

        new_channel = thread or channel
        if new_channel is not None:
            war["channel_id"] = new_channel.id
            applied.append("channel")

        if not applied:
            await interaction.response.send_message(
                "No updates supplied. Provide at least one field to change.",
                ephemeral=True,
            )
            return

        self._save(wars)

        embed = self._war_embed(war, title=f"War Updated — {_format_war_name(war)}")
        embed.add_field(
            name="Updated Fields",
            value=", ".join(sorted(applied)),
            inline=False,
        )
        await interaction.response.send_message(
            embed=embed, allowed_mentions=discord.AllowedMentions.none()
        )

    # === COMMAND: /war resolve ===
    @app_commands.command(name="resolve", description="Resolve a war initiative step.")
    @app_commands.guild_only()
    async def war_resolve(self, interaction: discord.Interaction, war_id: int) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        view = WarResolutionView(interaction.user, _format_war_name(war))
        await interaction.response.send_message(
            content=(
                f"Resolving **{_format_war_name(war)}**.\n"
                "Step 1 — choose the winner."
            ),
            view=view,
            ephemeral=True,
        )
        view.message = await interaction.original_response()

        result = await view.wait_for_result()
        if result is None:
            await interaction.followup.send(
                "Resolution cancelled or timed out.", ephemeral=True
            )
            return

        previous_momentum = int(war.get("momentum", 0))
        last_winner = _derive_last_winner(previous_momentum)
        winner = result["winner"]
        shift_value = int(result["shift"])

        if winner == "attacker":
            new_momentum = calculate_momentum(previous_momentum, "attacker", last_winner)
            warbar_delta = shift_value
            embed_color = discord.Color.green()
            outcome_summary = f"Attacker wins ({result['victory_label']})"
        elif winner == "defender":
            new_momentum = calculate_momentum(previous_momentum, "defender", last_winner)
            warbar_delta = shift_value
            embed_color = discord.Color.red()
            outcome_summary = f"Defender wins ({result['victory_label']})"
        else:
            new_momentum = 0
            warbar_delta = 0
            embed_color = discord.Color.gold()
            outcome_summary = "Stalemate"

        war["warbar"] = clamp(int(war.get("warbar", 0)) + warbar_delta, -100, 100)
        war["momentum"] = new_momentum
        war["initiative"] = _flip_initiative(war.get("initiative", "attacker"))
        war["last_update"] = update_timestamp()
        war["notes"] = result["notes"]

        self._save(wars)

        momentum_note = _war_momentum_summary(new_momentum)
        embed = discord.Embed(
            title=f"📜 War Resolution — {_format_war_name(war)}",
            color=embed_color,
        )
        embed.description = _warbar_summary(int(war["warbar"]))
        embed.add_field(name="🎲 Outcome", value=outcome_summary, inline=False)
        embed.add_field(
            name="📈 WarBar Shift",
            value=f"{warbar_delta:+d} (Momentum {momentum_note})",
            inline=False,
        )
        embed.add_field(
            name="🎯 New Initiative", value=war["initiative"].title(), inline=True
        )
        embed.add_field(name="🕒 Updated", value=war["last_update"], inline=True)
        notes = result["notes"]
        if notes:
            embed.add_field(name="🧾 Notes", value=notes, inline=False)

        await interaction.followup.send(
            embed=embed,
            allowed_mentions=discord.AllowedMentions.none(),
        )

    # === COMMAND: /war next ===
    @app_commands.command(name="next", description="Advance to the next side's initiative.")
    @app_commands.guild_only()
    async def war_next(self, interaction: discord.Interaction, war_id: int) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        war["initiative"] = _flip_initiative(war.get("initiative", "attacker"))
        war["last_update"] = update_timestamp()
        self._save(wars)

        await interaction.response.send_message(
            f"Initiative flipped to **{war['initiative'].title()}** for {_format_war_name(war)}.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    # === COMMAND: /war end ===
    @app_commands.command(name="end", description="End tracking for a war.")
    @app_commands.guild_only()
    async def war_end(self, interaction: discord.Interaction, war_id: int) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        wars = [existing for existing in wars if existing.get("id") != war_id]
        self._save(wars)
        # TODO: Implement war archival into wars_archive.json

        await interaction.response.send_message(
            f"War **{_format_war_name(war)}** has been removed from active tracking.",
            allowed_mentions=discord.AllowedMentions.none(),
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WarCommands(bot))
