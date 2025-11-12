"""Background scheduler for stagnation reminders."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional

import discord
from discord.ext import tasks
from zoneinfo import ZoneInfo

from .data_manager import load_wars
from .time_manager import (
    advance_turns,
    collect_due_timers,
    format_time,
    is_paused,
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

    async def _sleep_until_midnight(self) -> None:
        """Align the scheduler to the next midnight in Eastern time."""
        now = datetime.now(EASTERN)
        next_day = now.date() + timedelta(days=1)
        midnight_eastern = datetime.combine(
            next_day,
            datetime.min.time(),
            tzinfo=EASTERN,
        )
        await discord.utils.sleep_until(midnight_eastern.astimezone(timezone.utc))

    @tasks.loop(hours=24)
    async def check_loop(self) -> None:
        """Loop body that checks for stale wars and due timers every day."""
        await self._perform_check()

    @check_loop.before_loop
    async def before_check_loop(self) -> None:
        await self.bot.wait_until_ready()
        await self._sleep_until_midnight()
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

        # Check if time is paused
        state = load_time_state()
        if is_paused(state):
            log.info("Time is paused - skipping scheduled checks")
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
            allowed_mentions = discord.AllowedMentions(
                roles=[discord.Object(id=int(self.gm_role_id))]
            )
            try:
                await channel.send(
                    content=gm_mention, embed=embed, allowed_mentions=allowed_mentions
                )
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

            mention_pref = timer.get("mention", "gms")
            mention_text = ""
            allowed_mentions = discord.AllowedMentions.none()

            if mention_pref == "gms" and self.gm_role_id:
                gm_mention = f"<@&{int(self.gm_role_id)}>"
                mention_text = gm_mention
                allowed_mentions = discord.AllowedMentions(
                    roles=[discord.Object(id=int(self.gm_role_id))]
                )
            elif mention_pref == "creator":
                creator_id = timer.get("created_by")
                if creator_id:
                    mention_text = f"<@{int(creator_id)}>"
                    allowed_mentions = discord.AllowedMentions(
                        users=[discord.Object(id=int(creator_id))]
                    )

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
                await channel.send(
                    content=mention_text or None,
                    embed=embed,
                    allowed_mentions=allowed_mentions,
                )
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
        allowed_mentions = discord.AllowedMentions(
            roles=[discord.Object(id=int(self.gm_role_id))]
        )
        try:
            await channel.send(
                content=" ".join(mentions), embed=embed, allowed_mentions=allowed_mentions
            )
        except discord.HTTPException as exc:
            log.warning("Failed to send time advance alert: %s", exc)

    # === NPC AUTO-RESOLUTION LOOP ===

    def start_npc_loop(self) -> None:
        """Start the NPC auto-resolution loop."""
        if not self.npc_resolution_loop.is_running():
            self.npc_resolution_loop.start()
            log.info("NPC auto-resolution loop started.")

    def stop_npc_loop(self) -> None:
        """Stop the NPC auto-resolution loop."""
        if self.npc_resolution_loop.is_running():
            self.npc_resolution_loop.cancel()
            log.info("NPC auto-resolution loop stopped.")

    @tasks.loop(hours=1)
    async def npc_resolution_loop(self) -> None:
        """Check for NPC wars that need auto-resolution every hour."""
        await self._check_npc_wars()

    @npc_resolution_loop.before_loop
    async def before_npc_loop(self) -> None:
        await self.bot.wait_until_ready()
        log.info("NPC auto-resolution scheduler ready.")

    async def _check_npc_wars(self) -> None:
        """Check all wars for NPC auto-resolution eligibility."""
        from .data_manager import save_wars
        from .npc_ai import choose_npc_actions, update_learning_data
        from .npc_narratives import generate_npc_narrative

        # Check if time is paused
        state = load_time_state()
        if is_paused(state):
            log.info("Time is paused - skipping NPC auto-resolution")
            return

        wars = load_wars()
        if not wars:
            return

        now = datetime.now(timezone.utc)

        for war in wars:
            auto_config = war.get("auto_resolve", {})
            if not auto_config.get("enabled", False):
                continue  # Skip non-auto wars

            # Check if both sides are NPCs
            npc_config = war.get("npc_config", {})
            attacker_is_npc = npc_config.get("attacker", {}).get("enabled", False)
            defender_is_npc = npc_config.get("defender", {}).get("enabled", False)

            if not (attacker_is_npc and defender_is_npc):
                continue  # Skip if not NPC vs NPC

            # Check if interval has passed
            last_resolution = auto_config.get("last_resolution")
            interval_hours = auto_config.get("interval_hours", 12)

            if last_resolution:
                try:
                    last_time = datetime.fromisoformat(last_resolution)
                    if last_time.tzinfo is None:
                        last_time = last_time.replace(tzinfo=timezone.utc)

                    time_since = (now - last_time).total_seconds() / 3600

                    if time_since < interval_hours:
                        continue  # Not time yet
                except (ValueError, TypeError):
                    pass  # Treat as first resolution

            # Check turn limit
            turn_count = auto_config.get("turn_count", 0)
            max_turns = auto_config.get("max_turns", 50)

            if turn_count >= max_turns:
                # Defender auto-wins
                await self._end_npc_war_by_turn_limit(war)
                save_wars(wars)
                continue

            # Perform NPC vs NPC resolution
            try:
                await self._resolve_npc_war(war, npc_config)

                # Update auto-resolve tracking
                war["auto_resolve"]["last_resolution"] = now.isoformat()
                war["auto_resolve"]["turn_count"] = turn_count + 1

                save_wars(wars)
                log.info("Auto-resolved NPC war #%s (turn %d)", war.get("id"), turn_count + 1)

            except Exception as exc:
                log.error("Failed to auto-resolve NPC war #%s: %s", war.get("id"), exc)

    async def _resolve_npc_war(self, war: dict, npc_config: dict) -> None:
        """Resolve one turn of NPC vs NPC combat."""
        import random
        from .combat import calculate_damage_from_margin, calculate_modifiers, cleanup_expired_modifiers
        from .utils import update_dual_momentum, format_tactical_momentum, format_strategic_momentum, render_warbar, update_timestamp
        from .npc_ai import choose_npc_actions, update_learning_data
        from .npc_narratives import generate_npc_narrative

        # Generate actions for BOTH NPCs
        attacker_config = npc_config.get("attacker", {})
        defender_config = npc_config.get("defender", {})

        attacker_learning = attacker_config.get("learning_data", {})
        defender_learning = defender_config.get("learning_data", {})

        # Choose actions
        attacker_main, attacker_minor = choose_npc_actions(
            war, "attacker",
            attacker_config.get("archetype", "nato"),
            attacker_config.get("personality", "balanced"),
            attacker_learning
        )

        defender_main, defender_minor = choose_npc_actions(
            war, "defender",
            defender_config.get("archetype", "nato"),
            defender_config.get("personality", "balanced"),
            defender_learning
        )

        # Generate narratives
        attacker_narrative = generate_npc_narrative(
            war, "attacker", attacker_main, attacker_minor,
            attacker_config.get("archetype", "nato"),
            attacker_config.get("tech_level", "modern"),
            attacker_config.get("personality", "balanced")
        )

        defender_narrative = generate_npc_narrative(
            war, "defender", defender_main, defender_minor,
            defender_config.get("archetype", "nato"),
            defender_config.get("tech_level", "modern"),
            defender_config.get("personality", "balanced")
        )

        # Calculate modifiers
        attacker_mods, attacker_total = calculate_modifiers(war, "attacker", attacker_main, attacker_minor)
        defender_mods, defender_total = calculate_modifiers(war, "defender", defender_main, defender_minor)

        # Handle sabotage
        if attacker_minor == "sabotage":
            defender_mods.append(("Enemy Sabotage", -1))
            defender_total -= 1
        if defender_minor == "sabotage":
            attacker_mods.append(("Enemy Sabotage", -1))
            attacker_total -= 1

        # Roll dice
        attacker_roll = random.randint(1, 20)
        defender_roll = random.randint(1, 20)

        # Calculate totals
        attacker_result = attacker_roll + attacker_total
        defender_result = defender_roll + defender_total
        difference = attacker_result - defender_result

        # Determine winner
        if abs(difference) <= 2:
            winner = "stalemate"
            damage = 0
        elif difference > 0:
            winner = "attacker"
            strategic_mom = war.get("strategic_momentum", {}).get("attacker", 0)
            damage = calculate_damage_from_margin(abs(difference), strategic_mom)
        else:
            winner = "defender"
            strategic_mom = war.get("strategic_momentum", {}).get("defender", 0)
            damage = calculate_damage_from_margin(abs(difference), strategic_mom)

        # Apply defense stance damage reduction
        if attacker_main == "defend" and winner == "defender":
            damage = int(damage * 0.5)
        elif defender_main == "defend" and winner == "attacker":
            damage = int(damage * 0.5)

        # Apply damage to warbar
        if winner == "attacker":
            war["warbar"] = min(war["warbar"] + damage, war.get("max_value", 100))
        elif winner == "defender":
            war["warbar"] = max(war["warbar"] - damage, -war.get("max_value", 100))

        # Update dual-track momentum
        update_dual_momentum(war, winner)

        # Clean up expired modifiers
        cleanup_expired_modifiers(war)

        # Update NPC learning data for BOTH sides
        for side in ("attacker", "defender"):
            side_config = npc_config.get(side, {})
            if side_config.get("enabled", False):
                if winner == "stalemate":
                    npc_outcome = "stalemate"
                elif winner == side:
                    npc_outcome = "win"
                else:
                    npc_outcome = "loss"

                npc_margin = abs(difference)
                if npc_outcome == "loss":
                    npc_margin = -npc_margin

                learning_data = side_config.get("learning_data", {})
                updated_learning = update_learning_data(learning_data, npc_outcome, npc_margin)
                war["npc_config"][side]["learning_data"] = updated_learning

        # Update war state
        war["last_update"] = update_timestamp()

        # Check for critical HP
        await self._check_critical_hp(war)

        # Post results to channel
        await self._post_npc_resolution(war, {
            "attacker_main": attacker_main,
            "attacker_minor": attacker_minor,
            "attacker_narrative": attacker_narrative,
            "attacker_roll": attacker_roll,
            "attacker_mods": attacker_mods,
            "attacker_total": attacker_result,
            "defender_main": defender_main,
            "defender_minor": defender_minor,
            "defender_narrative": defender_narrative,
            "defender_roll": defender_roll,
            "defender_mods": defender_mods,
            "defender_total": defender_result,
            "winner": winner,
            "damage": damage,
            "difference": difference
        })

    async def _check_critical_hp(self, war: dict) -> None:
        """Check if either side is at critical HP and notify GM."""
        auto_config = war.get("auto_resolve", {})
        if auto_config.get("critical_hp_notified", False):
            return  # Already notified

        # Calculate max possible damage
        attacker_strategic = war.get("strategic_momentum", {}).get("attacker", 0)
        defender_strategic = war.get("strategic_momentum", {}).get("defender", 0)

        # Conservative estimate: 30 base * 2.0 max multiplier = 60 max damage
        attacker_max_dmg = int(30 * (1.0 + attacker_strategic / 10))
        defender_max_dmg = int(30 * (1.0 + defender_strategic / 10))

        max_value = war.get("max_value", 100)
        current_warbar = war.get("warbar", 0)

        # Calculate effective HP
        attacker_hp = max_value + current_warbar
        defender_hp = max_value - current_warbar

        # Check critical
        attacker_critical = attacker_hp <= defender_max_dmg and attacker_hp > 0
        defender_critical = defender_hp <= attacker_max_dmg and defender_hp > 0

        if attacker_critical or defender_critical:
            gm_id = auto_config.get("created_by_gm_id")
            channel_id = war.get("channel_id") or self.time_channel_id

            if channel_id and gm_id:
                channel = await self._resolve_channel(int(channel_id))
                if channel:
                    critical_side = []
                    if attacker_critical:
                        critical_side.append(f"**{war.get('attacker', 'Attacker')}** (HP: ~{attacker_hp})")
                    if defender_critical:
                        critical_side.append(f"**{war.get('defender', 'Defender')}** (HP: ~{defender_hp})")

                    embed = discord.Embed(
                        title=f"⚠️ Critical HP Alert - War #{war.get('id')}",
                        description=f"The following faction(s) could be defeated in the next turn:\n" + "\n".join(critical_side),
                        color=discord.Color.red()
                    )

                    embed.add_field(
                        name="War",
                        value=f"{war.get('attacker', 'Attacker')} vs {war.get('defender', 'Defender')}",
                        inline=False
                    )

                    embed.add_field(
                        name="Current Warbar",
                        value=f"{current_warbar:+d}/{max_value}",
                        inline=True
                    )

                    embed.add_field(
                        name="Turn",
                        value=f"{auto_config.get('turn_count', 0)}/{auto_config.get('max_turns', 50)}",
                        inline=True
                    )

                    content = f"<@{gm_id}>"
                    allowed_mentions = discord.AllowedMentions(users=[discord.Object(id=int(gm_id))])

                    try:
                        await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
                        war["auto_resolve"]["critical_hp_notified"] = True
                    except discord.HTTPException as exc:
                        log.warning("Failed to send critical HP notification: %s", exc)

    async def _post_npc_resolution(self, war: dict, results: dict) -> None:
        """Post NPC resolution results to war channel."""
        from .utils import render_warbar, format_tactical_momentum, format_strategic_momentum

        channel_id = war.get("channel_id") or self.time_channel_id
        if not channel_id:
            return

        channel = await self._resolve_channel(int(channel_id))
        if not channel:
            return

        embed = discord.Embed(
            title=f"⚔️ NPC WAR RESOLUTION: {war.get('name', 'Unnamed War')}",
            description=f"**Turn {war.get('auto_resolve', {}).get('turn_count', 0)}**",
            color=discord.Color.gold()
        )

        # Narratives
        embed.add_field(
            name=f"📖 {war.get('attacker', 'Attacker')} (NPC)",
            value=results["attacker_narrative"][:1024],
            inline=False
        )

        embed.add_field(
            name=f"📖 {war.get('defender', 'Defender')} (NPC)",
            value=results["defender_narrative"][:1024],
            inline=False
        )

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # Roll results
        attacker_mods_str = "\n".join(f"{name}: {val:+d}" for name, val in results["attacker_mods"])
        defender_mods_str = "\n".join(f"{name}: {val:+d}" for name, val in results["defender_mods"])

        embed.add_field(
            name="🎲 Attacker Roll",
            value=f"Roll: {results['attacker_roll']}\n{attacker_mods_str}\n**Total: {results['attacker_total']}**",
            inline=True
        )

        embed.add_field(
            name="🎲 Defender Roll",
            value=f"Roll: {results['defender_roll']}\n{defender_mods_str}\n**Total: {results['defender_total']}**",
            inline=True
        )

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # Result
        if results["winner"] == "stalemate":
            result_text = "🤝 **Stalemate!**"
        else:
            result_text = f"🏆 **{results['winner'].title()} Victory!**\nDamage: {results['damage']} warbar"

        embed.add_field(name="Result", value=result_text, inline=False)

        # Warbar
        max_value = war.get("max_value", 100)
        embed.add_field(
            name="War Progress",
            value=render_warbar(war["warbar"], max_value=max_value) + f"\n{war['warbar']:+d}/{max_value}",
            inline=False
        )

        # Momentum
        embed.add_field(
            name="Momentum",
            value=(
                f"Tactical: {format_tactical_momentum(war.get('tactical_momentum', 0))}\n"
                f"Strategic: {format_strategic_momentum(war['strategic_momentum']['attacker'], war['strategic_momentum']['defender'])}"
            ),
            inline=False
        )

        try:
            await channel.send(embed=embed)
        except discord.HTTPException as exc:
            log.warning("Failed to post NPC resolution: %s", exc)

    async def _end_npc_war_by_turn_limit(self, war: dict) -> None:
        """End an NPC war that reached turn limit - defender wins."""
        war["auto_resolve"]["enabled"] = False

        gm_id = war.get("auto_resolve", {}).get("created_by_gm_id")
        channel_id = war.get("channel_id") or self.time_channel_id

        if channel_id:
            channel = await self._resolve_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    title="⏱️ NPC War Concluded: Turn Limit Reached",
                    description=(
                        f"**{war.get('defender', 'Defender')} successfully repelled {war.get('attacker', 'Attacker')}**\n\n"
                        f"The conflict reached {war['auto_resolve']['max_turns']} turns without resolution. "
                        f"The defending forces held their ground, and the attackers were unable to achieve their objectives. "
                        f"Status quo maintained."
                    ),
                    color=discord.Color.blue()
                )

                embed.add_field(
                    name="War Details",
                    value=f"War #{war.get('id')}: {war.get('name', 'Unnamed War')}",
                    inline=False
                )

                content = f"<@{gm_id}>" if gm_id else None
                allowed_mentions = discord.AllowedMentions(users=[discord.Object(id=int(gm_id))]) if gm_id else None

                try:
                    await channel.send(content=content, embed=embed, allowed_mentions=allowed_mentions)
                except discord.HTTPException as exc:
                    log.warning("Failed to send turn limit notification: %s", exc)
