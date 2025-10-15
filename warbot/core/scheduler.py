"""Background scheduler for stagnation reminders."""

from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Optional

import discord
from discord.ext import tasks
from zoneinfo import ZoneInfo

from .data_manager import load_wars
from .time_manager import (
    advance_turns,
    collect_due_timers,
    format_time,
    load_time_state,
    save_time_state,
)

log = logging.getLogger(__name__)
EASTERN = ZoneInfo("America/New_York")


class StagnationScheduler:
    """Hourly loop that alerts GMs when wars stagnate and timers mature."""

    def __init__(
        self, bot: discord.Client, gm_role_id: int, time_channel_id: int
    ) -> None:
        self.bot = bot
        self.gm_role_id = gm_role_id
        self.time_channel_id = time_channel_id
        self.check_loop.change_interval(hours=24)

    def start(self) -> None:
        """Start the stagnation loop if not already running."""
        if not self.check_loop.is_running():
            self.check_loop.start()
            log.info("Stagnation check loop started.")

    def stop(self) -> None:
        """Stop the stagnation loop if running."""
        if self.check_loop.is_running():
            self.check_loop.cancel()
            log.info("Stagnation check loop stopped.")

    async def _resolve_channel(
        self, channel_id: int
    ) -> Optional[discord.abc.Messageable]:
        """Fetch a messageable channel or thread by ID."""
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except discord.HTTPException:
                log.warning("Unable to fetch channel with ID %s", channel_id)
                return None
        if not isinstance(channel, discord.abc.Messageable):
            log.warning("Channel %s is not messageable.", channel_id)
            return None
        return channel

    async def resolve_channel(
        self, channel_id: int
    ) -> Optional[discord.abc.Messageable]:
        """Public helper used by cogs to fetch channels safely."""
        return await self._resolve_channel(channel_id)

    @tasks.loop(hours=24)
    async def check_loop(self) -> None:
        """Loop body that checks for stale wars and due timers every 24 hours."""
        await self._perform_check()

    @check_loop.before_loop
    async def before_check_loop(self) -> None:
        await self.bot.wait_until_ready()
        log.info("Stagnation scheduler ready; awaiting daily tick.")

    async def run_once(self) -> None:
        """Run a single stagnation check immediately."""
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()
        await self._perform_check()

    async def check_timers_now(self) -> None:
        """Run the timer check immediately."""
        if not self.bot.is_ready():
            await self.bot.wait_until_ready()
        await self._check_time_timers()

    async def _perform_check(self) -> None:
        """Shared check logic used by both the loop and the force command."""
        if not self.bot.is_ready():
            return

        await self._check_war_stagnation()
        await self._advance_rp_time_if_needed()
        await self._check_time_timers()

    async def _check_war_stagnation(self) -> None:
        wars = load_wars()
        if not wars:
            return

        gm_mention = f"<@&{self.gm_role_id}>"
        now = datetime.now(timezone.utc)

        for war in wars:
            target_channel_id = war.get("channel_id") or self.time_channel_id
            if target_channel_id is None:
                log.warning(
                    "War %s does not have a channel_id and no fallback channel is set.",
                    war.get("name"),
                )
                continue

            last_update_raw = war.get("last_update")
            if not last_update_raw:
                continue
            try:
                last_update = datetime.fromisoformat(last_update_raw)
            except ValueError:
                log.warning("Invalid timestamp for war %s", war.get("name"))
                continue

            if last_update.tzinfo is None:
                last_update = last_update.replace(tzinfo=timezone.utc)

            hours_since = (now - last_update).total_seconds() / 3600
            if hours_since < 24:
                continue

            channel = await self._resolve_channel(int(target_channel_id))
            if channel is None:
                continue

            embed = discord.Embed(
                title="⚠️ War Stagnation Detected",
                description=(
                    f"It’s been 24h since the last initiative update for "
                    f"“{war.get('name', 'Unknown War')}.”"
                ),
                color=discord.Color.orange(),
            )
            embed.add_field(
                name="Hours Since Update", value=f"{hours_since:.1f}h", inline=False
            )
            embed.add_field(
                name="Call to Action",
                value=(
                    "Please resolve or advance initiative using `/war resolve` "
                    "or `/war next`."
                ),
                inline=False,
            )
            try:
                await channel.send(content=gm_mention, embed=embed)
            except discord.HTTPException as exc:
                log.warning("Failed to send stagnation alert: %s", exc)

    async def _check_time_timers(self) -> None:
        state = load_time_state()
        due_timers = collect_due_timers(state)
        if not due_timers:
            return

        save_time_state(state)
        for timer in due_timers:
            target_channel_id = timer.get("channel_id") or self.time_channel_id
            if target_channel_id is None:
                continue

            channel = await self._resolve_channel(int(target_channel_id))
            if channel is None:
                continue

            gm_mentions = [f"<@&{self.gm_role_id}>"]
            creator_id = timer.get("created_by")
            if creator_id:
                gm_mentions.append(f"<@{int(creator_id)}>")
            mention_text = " ".join(gm_mentions)

            embed = discord.Embed(
                title="⏰ RP Timer Triggered",
                description=timer.get("description", "Scheduled reminder"),
                color=discord.Color.blue(),
            )
            embed.add_field(
                name="When",
                value=format_time(state),
                inline=False,
            )
            embed.add_field(
                name="Timer ID",
                value=str(timer.get("id")),
                inline=True,
            )
            embed.add_field(
                name="Scheduled Turns",
                value=str(timer.get("turns")),
                inline=True,
            )

            try:
                await channel.send(content=mention_text, embed=embed)
            except discord.HTTPException as exc:
                log.warning("Failed to send timer alert: %s", exc)

    async def _advance_rp_time_if_needed(self) -> None:
        state = load_time_state()
        today = datetime.now(EASTERN).date()
        last_auto_str = state.get("last_auto_date")

        if not last_auto_str:
            state["last_auto_date"] = today.isoformat()
            save_time_state(state)
            return

        try:
            last_date = date.fromisoformat(last_auto_str)
        except ValueError:
            last_date = today

        if today <= last_date:
            return

        turns = (today - last_date).days
        if turns <= 0:
            return

        state = advance_turns(state, turns)
        state["last_auto_date"] = today.isoformat()
        save_time_state(state)

        await self._announce_time_update(state, turns)

    async def _announce_time_update(self, state: dict, turns: int) -> None:
        channel_id = self.time_channel_id
        if channel_id is None:
            return

        channel = await self._resolve_channel(int(channel_id))
        if channel is None:
            return

        embed = discord.Embed(
            title="🗓️ RP Time Advanced",
            description=format_time(state),
            color=discord.Color.teal(),
        )
        embed.add_field(name="Year", value=str(state.get("year")), inline=True)
        embed.add_field(
            name="Season", value=f"{state.get('season')}/4", inline=True
        )
        embed.add_field(
            name="Advance",
            value=f"{turns} season{'s' if turns != 1 else ''} (auto)",
            inline=False,
        )
        embed.set_footer(text="Advanced automatically at midnight ET")

        mentions = [f"<@&{self.gm_role_id}>"]
        try:
            await channel.send(content=" ".join(mentions), embed=embed)
        except discord.HTTPException as exc:
            log.warning("Failed to send time advance alert: %s", exc)
