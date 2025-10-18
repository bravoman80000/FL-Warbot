"""Slash commands focused on RP time management."""

from __future__ import annotations

from typing import List, Optional

import discord
from discord import app_commands
from discord.ext import commands

from ..core import time_manager

TIMER_NOTIFY_CHOICES: List[app_commands.Choice[str]] = [
    app_commands.Choice(name="Only me", value="creator"),
    app_commands.Choice(name="All GMs", value="gms"),
]
TIMER_NOTIFY_LABELS = {
    "creator": "Only me",
    "gms": "All GMs",
}


class TimeCommands(commands.GroupCog, name="time"):
    """Cog implementing `/time` command group."""

    def __init__(self, bot: commands.Bot, scheduler) -> None:
        super().__init__()
        self.bot = bot
        self.scheduler = scheduler

    def _load_state(self) -> dict:
        return time_manager.load_time_state()

    def _save_state(self, state: dict) -> None:
        time_manager.save_time_state(state)

    def _build_time_embed(self, title: str, state: dict) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=time_manager.format_time(state),
            color=discord.Color.teal(),
        )
        embed.add_field(name="Year", value=str(state.get("year")), inline=True)
        embed.add_field(
            name="Season", value=f"{state.get('season')}/4", inline=True
        )
        updated = state.get("updated_at") or "Unrecorded"
        embed.set_footer(text=f"Last change: {updated}")
        return embed

    async def _broadcast_time_update(
        self, state: dict, title: str, announce: bool
    ) -> None:
        if not announce:
            return

        channel_id = getattr(self.scheduler, "time_channel_id", None)
        if not channel_id:
            return

        channel = await self.scheduler.resolve_channel(int(channel_id))
        if channel is None:
            return

        embed = self._build_time_embed(title, state)
        await channel.send(embed=embed)

    # === COMMAND: /time show ===
    @app_commands.command(name="show", description="Display the current RP time.")
    @app_commands.guild_only()
    async def time_show(self, interaction: discord.Interaction) -> None:
        state = self._load_state()
        embed = self._build_time_embed("Current RP Time", state)
        await interaction.response.send_message(embed=embed)

    # === COMMAND: /time set ===
    @app_commands.command(name="set", description="Set the RP year and season.")
    @app_commands.guild_only()
    async def time_set(
        self,
        interaction: discord.Interaction,
        year: app_commands.Range[int, 0, 10000],
        season: app_commands.Range[int, 1, 4],
        announce: Optional[bool] = True,
    ) -> None:
        state = self._load_state()
        time_manager.set_time(state, year, season)
        self._save_state(state)

        embed = self._build_time_embed("RP Time Updated", state)
        await interaction.response.send_message(
            embed=embed, allowed_mentions=discord.AllowedMentions.none()
        )

        await self.scheduler.check_timers_now()
        await self._broadcast_time_update(state, "RP Time Updated", bool(announce))

    # === COMMAND: /time skip ===
    @app_commands.command(name="skip", description="Advance the RP clock by a number of turns.")
    @app_commands.guild_only()
    @app_commands.describe(amount="How many units to advance", unit="Choose seasons or years")
    @app_commands.choices(
        unit=[
            app_commands.Choice(name="Seasons", value="season"),
            app_commands.Choice(name="Years", value="year"),
        ]
    )
    async def time_skip(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[int, 1, 200],
        unit: app_commands.Choice[str],
        announce: Optional[bool] = True,
    ) -> None:
        state = self._load_state()
        turns = amount * 4 if unit.value == "year" else amount
        time_manager.advance_turns(state, turns)
        self._save_state(state)

        embed = self._build_time_embed("RP Time Advanced", state)
        embed.add_field(
            name="Advance Applied",
            value=f"{amount} {unit.name.lower()}",
            inline=False,
        )
        await interaction.response.send_message(
            embed=embed, allowed_mentions=discord.AllowedMentions.none()
        )

        await self.scheduler.check_timers_now()
        await self._broadcast_time_update(state, "RP Time Advanced", bool(announce))

    # === COMMAND: /time timer_add ===
    @app_commands.command(
        name="timer_add",
        description="Set a reminder after a number of RP turns.",
    )
    @app_commands.guild_only()
    @app_commands.describe(
        notify="Choose who should be mentioned when the timer triggers."
    )
    @app_commands.choices(notify=TIMER_NOTIFY_CHOICES)
    async def time_timer_add(
        self,
        interaction: discord.Interaction,
        turns: app_commands.Range[int, 1, 100],
        description: str,
        channel: Optional[discord.abc.GuildChannel] = None,
        thread: Optional[discord.Thread] = None,
        notify: Optional[app_commands.Choice[str]] = None,
    ) -> None:
        if len(description) > 200:
            await interaction.response.send_message(
                "Description must be 200 characters or fewer.", ephemeral=True
            )
            return

        state = self._load_state()
        target_channel = thread or channel or interaction.channel
        if target_channel is None:
            await interaction.response.send_message(
                "Unable to determine a channel for the timer reminder.",
                ephemeral=True,
            )
            return

        notify_target = (
            notify.value if isinstance(notify, app_commands.Choice) else "gms"
        )

        try:
            timer = time_manager.add_timer(
                state,
                turns_from_now=turns,
                description=description,
                channel_id=target_channel.id,
                created_by=interaction.user.id,
                mention=notify_target,
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return

        self._save_state(state)

        embed = discord.Embed(
            title="Timer Created",
            description=description,
            color=discord.Color.purple(),
        )
        embed.add_field(name="Timer ID", value=str(timer["id"]), inline=True)
        embed.add_field(name="Turns Until Alert", value=str(turns), inline=True)
        embed.add_field(
            name="Target Channel",
            value=f"<#{target_channel.id}>",
            inline=False,
        )
        embed.add_field(
            name="Will Notify",
            value=TIMER_NOTIFY_LABELS.get(notify_target, "All GMs"),
            inline=False,
        )

        await interaction.response.send_message(
            embed=embed, allowed_mentions=discord.AllowedMentions.none(), ephemeral=True
        )

    # === COMMAND: /time timer_list ===
    @app_commands.command(
        name="timer_list", description="List all scheduled RP time reminders."
    )
    @app_commands.guild_only()
    async def time_timer_list(self, interaction: discord.Interaction) -> None:
        state = self._load_state()
        timers = time_manager.list_timers(state)
        if not timers:
            await interaction.response.send_message(
                "No timers are currently scheduled.", ephemeral=True
            )
            return

        current_turn = time_manager.current_turn_index(state)
        embed = discord.Embed(
            title="Scheduled RP Timers",
            color=discord.Color.purple(),
        )

        for timer in timers:
            remaining = max(0, int(timer.get("trigger_turn")) - current_turn)
            channel_id = timer.get("channel_id")
            notify_target = timer.get("mention", "gms")
            embed.add_field(
                name=f"Timer #{timer.get('id')} — {remaining} turns remaining",
                value=(
                    f"{timer.get('description', 'Reminder')}\n"
                    f"Channel: <#{int(channel_id)}>\n"
                    f"Notifies: {TIMER_NOTIFY_LABELS.get(notify_target, 'All GMs')}"
                ),
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === COMMAND: /time timer_cancel ===
    @app_commands.command(
        name="timer_cancel",
        description="Cancel a scheduled RP timer by its ID.",
    )
    @app_commands.guild_only()
    async def time_timer_cancel(
        self, interaction: discord.Interaction, timer_id: int
    ) -> None:
        state = self._load_state()
        if not time_manager.cancel_timer(state, timer_id):
            await interaction.response.send_message(
                f"No timer found with ID {timer_id}.", ephemeral=True
            )
            return

        self._save_state(state)
        await interaction.response.send_message(
            f"Timer #{timer_id} cancelled.", ephemeral=True
        )


async def setup(bot: commands.Bot) -> None:
    scheduler = getattr(bot, "stagnation_scheduler", None)
    if scheduler is None:
        raise RuntimeError("Stagnation scheduler has not been initialised on the bot.")
    await bot.add_cog(TimeCommands(bot, scheduler))
