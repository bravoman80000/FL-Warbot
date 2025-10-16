"""Slash commands for managing wars."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import find_war_by_id, load_wars, save_wars
from ..core.utils import (
    calculate_momentum,
    clamp,
    render_health_bar,
    render_warbar,
    update_timestamp,
)

SIDE_CHOICES: List[app_commands.Choice[str]] = [
    app_commands.Choice(name="Attacker", value="attacker"),
    app_commands.Choice(name="Defender", value="defender"),
]

MENTION_MODE_CHOICES: List[app_commands.Choice[str]] = [
    app_commands.Choice(name="Team Roles", value="team"),
    app_commands.Choice(name="Individual Participants", value="individual"),
]


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


def _truncate_label(label: str, limit: int = 100) -> str:
    if len(label) <= limit:
        return label
    return label[: limit - 1] + "…"


def _sanitize_positive(value: Optional[int], default: int) -> int:
    try:
        if value is None:
            raise ValueError
        sanitized = int(value)
    except (TypeError, ValueError):
        return default
    return max(1, sanitized)


def _format_participant_label(participant: Dict[str, Any]) -> str:
    name = participant.get("name") or "Unnamed"
    member_id = participant.get("member_id")
    if member_id:
        return f"{name} (<@{int(member_id)}>)"
    return name


def _format_participant_mention(participant: Dict[str, Any]) -> str:
    member_id = participant.get("member_id")
    if member_id:
        return f"<@{int(member_id)}>"
    return participant.get("name") or "Unnamed"


def _compute_role_name(war: Dict[str, Any], side: str) -> str:
    base = war.get("name") or f"War #{war.get('id')}"
    suffix = "Attacker" if side == "attacker" else "Defender"
    label = f"{base} — {suffix}"
    return label[:98]


def _format_roster_summary(war: Dict[str, Any], side: str) -> str:
    roster = war.get(f"{side}_roster") or []
    if not roster:
        return "None assigned"
    lines = []
    for idx, participant in enumerate(roster, start=1):
        lines.append(f"{idx}. {_format_participant_label(participant)}")
    return "\n".join(lines[:10]) + ("\n…" if len(lines) > 10 else "")


def _war_momentum_summary(momentum: int) -> str:
    if momentum > 0:
        return f"+{momentum} (Attacker)"
    if momentum < 0:
        return f"{momentum} (Defender)"
    return "0 (Neutral)"


def _normalize_mode(mode: Optional[str]) -> str:
    if not mode:
        return "pushpull_auto"

    value = str(mode).lower()
    legacy_map = {
        "pushpull": "pushpull_auto",
        "oneway": "oneway_auto",
        "attrition": "attrition_manual",
    }
    return legacy_map.get(value, value if value in MODE_LABELS else "pushpull_auto")


def _format_mode_label(mode: Optional[str]) -> str:
    normalized = _normalize_mode(mode)
    return MODE_LABELS.get(normalized, MODE_LABELS["pushpull_auto"])


def _get_max_value(war: Dict[str, Any]) -> int:
    try:
        return max(1, int(war.get("max_value", 100)))
    except (TypeError, ValueError):
        return 100


def _warbar_summary(war: Dict[str, Any]) -> str:
    mode = _normalize_mode(war.get("mode"))

    if mode == "attrition_manual":
        attacker_max = max(1, int(war.get("attacker_max_health", 100)))
        defender_max = max(1, int(war.get("defender_max_health", 100)))
        attacker_hp = clamp(int(war.get("attacker_health", attacker_max)), 0, attacker_max)
        defender_hp = clamp(int(war.get("defender_health", defender_max)), 0, defender_max)
        attacker_bar = render_health_bar(attacker_hp, attacker_max, side="attacker")
        defender_bar = render_health_bar(defender_hp, defender_max, side="defender")
        return (
            f"Attacker HP: {attacker_bar} ({attacker_hp}/{attacker_max})\n"
            f"Defender HP: {defender_bar} ({defender_hp}/{defender_max})"
        )

    max_value = _get_max_value(war)
    value = clamp(int(war.get("warbar", 0)), -max_value, max_value)
    bar = render_warbar(value, mode=mode, max_value=max_value)

    if mode.startswith("oneway"):
        percent = (value / max_value) * 100
        return f"{bar}\nProgress: {value}/{max_value} ({percent:.1f}%)"

    direction = "Neutral"
    if value > 0:
        direction = "Attacker Advantage"
    elif value < 0:
        direction = "Defender Advantage"
    return f"{bar}\nWarBar: {value:+d}/{max_value} ({direction})"


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
MODE_LABELS: Dict[str, str] = {
    "pushpull_auto": "Push & Pull (Auto Tug Of War)",
    "oneway_auto": "One Way Progress (Auto)",
    "pushpull_manual": "Push & Pull (Manual Tug Of War)",
    "oneway_manual": "One Way Progress (Manual)",
    "attrition_manual": "Attrition (Manual)",
}
MODE_CHOICES: List[app_commands.Choice[str]] = [
    app_commands.Choice(name=label, value=mode)
    for mode, label in MODE_LABELS.items()
]


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


class ManualResolutionModal(discord.ui.Modal):
    """Modal to capture manual shift values."""

    def __init__(self, parent_view: "WarResolutionView") -> None:
        super().__init__(title="Manual War Adjustment")
        self.parent_view = parent_view
        self.amount_input = discord.ui.TextInput(
            label="Shift Amount",
            placeholder="Enter numeric value (e.g. 3)",
            required=True,
            max_length=6,
        )
        self.notes_input = discord.ui.TextInput(
            label="Notes",
            placeholder="Context, casualties, reminders…",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )
        self.add_item(self.amount_input)
        self.add_item(self.notes_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw_value = (self.amount_input.value or "").strip()
        try:
            amount = int(raw_value)
        except ValueError:
            await interaction.response.send_message(
                "Please enter a whole number for the shift amount.", ephemeral=True
            )
            return

        self.parent_view.manual_amount = abs(amount)
        self.parent_view.notes = str(self.notes_input.value or "").strip()
        await interaction.response.send_message(
            "Manual adjustment captured. Posting results…", ephemeral=True
        )
        await self.parent_view.finalise()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await interaction.response.send_message(
            f"Failed to record manual input: {error}", ephemeral=True
        )
        await self.parent_view.cancel("An unexpected error occurred while saving the manual input.")


class WarResolutionView(discord.ui.View):
    """Interactive flow for /war resolve."""

    def __init__(
        self,
        user: discord.abc.User,
        war_name: str,
        *,
        manual_mode: bool = False,
        mode: str = "pushpull_auto",
        max_value: int = 100,
    ) -> None:
        super().__init__(timeout=300)
        self.user = user
        self.war_name = war_name
        self.manual_mode = manual_mode
        self.mode = mode
        self.max_value = max_value
        self.manual_amount: int = 0
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

        if not self.manual_mode:
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
        if self.manual_mode:
            self.disable_winner_buttons()
            if winner == "stalemate":
                await self.prompt_notes(interaction)
            else:
                modal = ManualResolutionModal(self)
                await interaction.response.send_modal(modal)
            return

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
        if self.manual_mode:
            if self.winner == "stalemate":
                victory_label = "Stalemate"
                net_shift = 0
            else:
                base_amount = abs(int(self.manual_amount))
                sign = 1 if self.winner == "attacker" else -1
                net_shift = base_amount * sign
                victory_label = f"Manual ({net_shift:+d})"
        else:
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
            "manual": self.manual_mode,
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


class AttritionActionButton(discord.ui.Button["AttritionResolutionView"]):
    def __init__(self, label: str, style: discord.ButtonStyle, action: str) -> None:
        super().__init__(label=label, style=style)
        self.action = action

    async def callback(self, interaction: discord.Interaction) -> None:
        assert self.view is not None
        await self.view.handle_action(interaction, self.action)


class AttritionAmountModal(discord.ui.Modal):
    def __init__(self, parent_view: "AttritionResolutionView", action: str) -> None:
        title_map = {
            "damage_attacker": "Damage Attacker",
            "damage_defender": "Damage Defender",
            "heal_attacker": "Heal Attacker",
            "heal_defender": "Heal Defender",
        }
        super().__init__(title=title_map.get(action, "Attrition Adjustment"))
        self.parent_view = parent_view
        self.action = action
        self.amount_input = discord.ui.TextInput(
            label="Amount",
            placeholder="Enter numeric value (e.g. 5)",
            required=True,
            max_length=6,
        )
        self.notes_input = discord.ui.TextInput(
            label="Notes",
            placeholder="Context or reminders…",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=500,
        )
        self.add_item(self.amount_input)
        self.add_item(self.notes_input)

    async def on_submit(self, interaction: discord.Interaction) -> None:
        raw_value = (self.amount_input.value or "").strip()
        try:
            amount = abs(int(raw_value))
        except ValueError:
            await interaction.response.send_message(
                "Please enter a whole number for the amount.", ephemeral=True
            )
            return

        self.parent_view.set_result(
            action=self.action,
            amount=amount,
            notes=str(self.notes_input.value or "").strip(),
        )
        await interaction.response.send_message(
            "Attrition adjustment captured. Posting results…", ephemeral=True
        )
        await self.parent_view.finalise()

    async def on_error(
        self, interaction: discord.Interaction, error: Exception
    ) -> None:
        await interaction.response.send_message(
            f"Failed to record attrition adjustment: {error}", ephemeral=True
        )
        await self.parent_view.cancel("An unexpected error occurred during attrition input.")


class AttritionResolutionView(discord.ui.View):
    def __init__(self, user: discord.abc.User, war_name: str) -> None:
        super().__init__(timeout=300)
        self.user = user
        self.war_name = war_name
        self.message: Optional[discord.Message] = None
        self.result: Optional[Dict[str, Any]] = None
        self._finished = asyncio.Event()

        self.add_item(AttritionActionButton("Damage Attacker", discord.ButtonStyle.danger, "damage_attacker"))
        self.add_item(AttritionActionButton("Damage Defender", discord.ButtonStyle.danger, "damage_defender"))
        self.add_item(AttritionActionButton("Heal Attacker", discord.ButtonStyle.success, "heal_attacker"))
        self.add_item(AttritionActionButton("Heal Defender", discord.ButtonStyle.success, "heal_defender"))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "Only the command invoker can use this resolution view.",
                ephemeral=True,
            )
            return False
        return True

    async def handle_action(self, interaction: discord.Interaction, action: str) -> None:
        modal = AttritionAmountModal(self, action)
        await interaction.response.send_modal(modal)

    def set_result(self, action: str, amount: int, notes: str) -> None:
        self.result = {
            "action": action,
            "amount": amount,
            "notes": notes,
        }

    async def finalise(self) -> None:
        self.disable_all()
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

    def disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

    async def on_timeout(self) -> None:
        await self.cancel("Resolution timed out — please run `/war resolve` again.")

    async def wait_for_result(self) -> Optional[Dict[str, Any]]:
        await self._finished.wait()
        return self.result


class WarCommands(commands.GroupCog, name="war"):
    """Cog implementing `/war` command group."""

    def __init__(self, bot: commands.Bot) -> None:
        super().__init__()
        self.bot = bot

    def _load(self) -> List[Dict[str, Any]]:
        wars = load_wars()
        mutated = False
        for war in wars:
            if self._apply_defaults(war):
                mutated = True
        if mutated:
            save_wars(wars)
        return wars

    def _save(self, wars: List[Dict[str, Any]]) -> None:
        save_wars(wars)

    def _next_war_id(self, wars: Sequence[Dict[str, Any]]) -> int:
        if not wars:
            return 1
        return max(int(war.get("id", 0)) for war in wars) + 1

    def _apply_defaults(self, war: Dict[str, Any]) -> bool:
        mutated = False
        for side in ("attacker", "defender"):
            roster_key = f"{side}_roster"
            if not isinstance(war.get(roster_key), list):
                war[roster_key] = []
                mutated = True
            index_key = f"{side}_turn_index"
            try:
                war[index_key] = int(war.get(index_key, 0))
            except (TypeError, ValueError):
                war[index_key] = 0
                mutated = True

        normalized_mode = _normalize_mode(war.get("mode"))
        if war.get("mode") != normalized_mode:
            war["mode"] = normalized_mode
            mutated = True

        if normalized_mode == "attrition_manual":
            attacker_max = _sanitize_positive(war.get("attacker_max_health"), 100)
            defender_max = _sanitize_positive(war.get("defender_max_health"), 100)
            attacker_hp = clamp(
                int(war.get("attacker_health", attacker_max)), 0, attacker_max
            )
            defender_hp = clamp(
                int(war.get("defender_health", defender_max)), 0, defender_max
            )

            if war.get("attacker_max_health") != attacker_max:
                war["attacker_max_health"] = attacker_max
                mutated = True
            if war.get("defender_max_health") != defender_max:
                war["defender_max_health"] = defender_max
                mutated = True
            if war.get("attacker_health") != attacker_hp:
                war["attacker_health"] = attacker_hp
                mutated = True
            if war.get("defender_health") != defender_hp:
                war["defender_health"] = defender_hp
                mutated = True
            diff = attacker_hp - defender_hp
            if war.get("warbar") != diff:
                war["warbar"] = diff
                mutated = True
        else:
            max_value = _sanitize_positive(war.get("max_value"), 100)
            if war.get("max_value") != max_value:
                war["max_value"] = max_value
                mutated = True
            warbar = clamp(int(war.get("warbar", 0)), -max_value, max_value)
            if war.get("warbar") != warbar:
                war["warbar"] = warbar
                mutated = True

        if "team_mentions" not in war:
            war["team_mentions"] = False
            mutated = True
        else:
            war["team_mentions"] = bool(war.get("team_mentions"))
        for side in ("attacker", "defender"):
            role_key = f"{side}_role_id"
            role_val = war.get(role_key)
            if role_val is None:
                continue
            try:
                war[role_key] = int(role_val)
            except (TypeError, ValueError):
                war[role_key] = None
                mutated = True

        return mutated

    def _get_roster(self, war: Dict[str, Any], side: str) -> List[Dict[str, Any]]:
        roster = war.get(f"{side}_roster")
        if not isinstance(roster, list):
            roster = []
            war[f"{side}_roster"] = roster
        return roster

    def _add_participant(
        self,
        war: Dict[str, Any],
        side: str,
        name: str,
        member: Optional[discord.abc.User],
    ) -> None:
        roster = self._get_roster(war, side)
        participant = {"name": name}
        if member is not None:
            participant["member_id"] = int(member.id)
        roster.append(participant)

    def _remove_participant(self, war: Dict[str, Any], side: str, index: int) -> Dict[str, Any]:
        roster = self._get_roster(war, side)
        if not roster:
            raise IndexError("Roster is empty")
        participant = roster.pop(index)
        key = f"{side}_turn_index"
        if roster:
            war[key] = war.get(key, 0) % len(roster)
        else:
            war[key] = 0
        return participant

    def _next_participant(
        self, war: Dict[str, Any], side: str, *, consume: bool
    ) -> Optional[Dict[str, Any]]:
        roster = self._get_roster(war, side)
        if not roster:
            return None
        key = f"{side}_turn_index"
        idx = int(war.get(key, 0)) % len(roster)
        participant = roster[idx]
        if consume:
            war[key] = (idx + 1) % len(roster)
        else:
            war[key] = idx % len(roster)
        return participant

    async def _resolve_role(
        self, guild: discord.Guild, war: Dict[str, Any], side: str
    ) -> Optional[discord.Role]:
        role_id = war.get(f"{side}_role_id")
        if role_id:
            role = guild.get_role(int(role_id))
            if role is not None:
                return role
        return None

    async def _ensure_role(
        self, guild: discord.Guild, war: Dict[str, Any], side: str
    ) -> discord.Role:
        role = await self._resolve_role(guild, war, side)
        if role is not None:
            return role

        role_name = _compute_role_name(war, side)
        role = await guild.create_role(
            name=role_name,
            mentionable=True,
            reason=f"Creating war team role for {_format_war_name(war)}",
        )
        war[f"{side}_role_id"] = int(role.id)
        return role

    async def _delete_role(
        self, guild: discord.Guild, war: Dict[str, Any], side: str
    ) -> None:
        role = await self._resolve_role(guild, war, side)
        if role is not None:
            try:
                await role.delete(reason=f"Cleaning up war team role for {_format_war_name(war)}")
            except discord.HTTPException:
                pass
        war[f"{side}_role_id"] = None

    async def _assign_member_to_role(
        self,
        guild: discord.Guild,
        war: Dict[str, Any],
        side: str,
        member: Optional[discord.Member],
    ) -> None:
        if member is None:
            return
        role = await self._ensure_role(guild, war, side)
        if role not in member.roles:
            try:
                await member.add_roles(role, reason=f"Assigned to {_format_war_name(war)} roster")
            except discord.HTTPException:
                pass

    async def _remove_member_from_role(
        self,
        guild: discord.Guild,
        war: Dict[str, Any],
        side: str,
        member_id: Optional[int],
    ) -> None:
        if member_id is None:
            return
        member = guild.get_member(int(member_id))
        if member is None:
            return
        role = await self._resolve_role(guild, war, side)
        if role and role in member.roles:
            try:
                await member.remove_roles(role, reason=f"Removed from {_format_war_name(war)} roster")
            except discord.HTTPException:
                pass

    async def _sync_roster_roles(
        self, guild: discord.Guild, war: Dict[str, Any], side: str
    ) -> None:
        roster = self._get_roster(war, side)
        role = await self._ensure_role(guild, war, side)
        members_in_roster = {
            int(p["member_id"]) for p in roster if p.get("member_id") is not None
        }
        for member in guild.members:
            if role not in member.roles and member.id in members_in_roster:
                try:
                    await member.add_roles(role, reason=f"Assigned to {_format_war_name(war)} roster")
                except discord.HTTPException:
                    pass
            elif role in member.roles and member.id not in members_in_roster:
                try:
                    await member.remove_roles(role, reason=f"Removed from {_format_war_name(war)} roster")
                except discord.HTTPException:
                    pass

    async def _rename_team_roles(self, guild: discord.Guild, war: Dict[str, Any]) -> None:
        if not war.get("team_mentions"):
            return
        for side in ("attacker", "defender"):
            role = await self._resolve_role(guild, war, side)
            if role is None:
                continue
            desired_name = _compute_role_name(war, side)
            if role.name != desired_name:
                try:
                    await role.edit(name=desired_name, reason="War name updated")
                except discord.HTTPException:
                    pass

    def _war_choice_results(self, current: str) -> List[app_commands.Choice[int]]:
        wars = sorted(self._load(), key=lambda w: int(w.get("id", 0)))
        current_lower = current.lower()
        choices: List[app_commands.Choice[int]] = []
        for war in wars:
            war_id = int(war.get("id", 0))
            label = f"#{war_id} — {_format_war_name(war)}"
            if current_lower and current_lower not in label.lower():
                continue
            choices.append(app_commands.Choice(name=_truncate_label(label), value=war_id))
            if len(choices) >= 25:
                break
        return choices

    def _participant_choice_results(
        self, war: Dict[str, Any], side: str, search: str
    ) -> List[app_commands.Choice[int]]:
        roster = self._get_roster(war, side)
        current_lower = search.lower()
        results: List[app_commands.Choice[int]] = []
        for idx, participant in enumerate(roster, start=1):
            label = f"{idx} — {_format_participant_label(participant)}"
            if current_lower and current_lower not in label.lower():
                continue
            results.append(
                app_commands.Choice(name=_truncate_label(label), value=idx)
            )
            if len(results) >= 25:
                break
        return results

    def _allowed_mentions_for_participant(
        self,
        war: Dict[str, Any],
        side: str,
        participant: Optional[Dict[str, Any]],
    ) -> discord.AllowedMentions:
        if war.get("team_mentions"):
            role_id = war.get(f"{side}_role_id")
            if role_id:
                return discord.AllowedMentions(
                    roles=[discord.Object(id=int(role_id))]
                )
        if participant and participant.get("member_id"):
            return discord.AllowedMentions(
                users=[discord.Object(id=int(participant["member_id"]))]
            )
        return discord.AllowedMentions.none()

    def _activation_display(
        self,
        war: Dict[str, Any],
        side: str,
        participant: Optional[Dict[str, Any]],
    ) -> str:
        if war.get("team_mentions") and war.get(f"{side}_role_id"):
            return f"<@&{int(war[f'{side}_role_id'])}>"
        if participant:
            return _format_participant_mention(participant)
        return "N/A"

    def _war_embed(self, war: Dict[str, Any], *, title: str) -> discord.Embed:
        embed = discord.Embed(
            title=title,
            description=_warbar_summary(war),
            color=discord.Color.blurple(),
        )
        embed.add_field(name="ID", value=str(war.get("id")), inline=True)
        embed.add_field(name="Theater", value=war.get("theater", "Unknown"), inline=True)
        embed.add_field(name="Mode", value=_format_mode_label(war.get("mode")), inline=True)
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
        attacker_next = self._next_participant(war, "attacker", consume=False)
        defender_next = self._next_participant(war, "defender", consume=False)
        embed.add_field(
            name="Next Attacker",
            value=self._activation_display(war, "attacker", attacker_next),
            inline=True,
        )
        embed.add_field(
            name="Next Defender",
            value=self._activation_display(war, "defender", defender_next),
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
        embed.add_field(
            name="Attacker Roster",
            value=_format_roster_summary(war, "attacker"),
            inline=False,
        )
        embed.add_field(
            name="Defender Roster",
            value=_format_roster_summary(war, "defender"),
            inline=False,
        )
        embed.set_footer(text=f"{war.get('attacker')} vs {war.get('defender')}")
        return embed

    # === COMMAND: /war start ===
    @app_commands.command(name="start", description="Start tracking a new war.")
    @app_commands.guild_only()
    @app_commands.choices(mode=MODE_CHOICES)
    @app_commands.describe(
        attacker="Faction initiating the conflict.",
        defender="Faction defending the conflict.",
        theater="Where the conflict occurs.",
        mode="War progression model.",
        name="Optional custom war name.",
        max_value="Optional health/progress total (defaults to 100).",
        attacker_health="Attrition: attacker starting health (defaults to 100).",
        defender_health="Attrition: defender starting health (defaults to 100).",
        team_mentions="Mention roster as team roles instead of individuals.",
    )
    async def war_start(
        self,
        interaction: discord.Interaction,
        attacker: str,
        defender: str,
        theater: str,
        mode: app_commands.Choice[str],
        name: Optional[str] = None,
        max_value: Optional[int] = None,
        attacker_health: Optional[int] = None,
        defender_health: Optional[int] = None,
        team_mentions: Optional[bool] = False,
    ) -> None:
        wars = self._load()
        war_id = self._next_war_id(wars)
        war_name = name or f"{attacker} vs {defender}"
        channel_id = interaction.channel_id
        mode_value = _normalize_mode(
            mode.value if isinstance(mode, app_commands.Choice) else str(mode)
        )
        max_total = _sanitize_positive(max_value, 100)
        attacker_max = _sanitize_positive(attacker_health, 100)
        defender_max = _sanitize_positive(defender_health, 100)
        war = {
            "id": war_id,
            "name": war_name,
            "attacker": attacker,
            "defender": defender,
            "theater": theater,
            "mode": mode_value,
            "warbar": 0,
            "max_value": max_total,
            "momentum": 0,
            "initiative": "attacker",
            "last_update": update_timestamp(),
            "notes": "",
            "channel_id": int(channel_id) if channel_id is not None else None,
            "attacker_roster": [],
            "defender_roster": [],
            "attacker_turn_index": 0,
            "defender_turn_index": 0,
            "team_mentions": bool(team_mentions),
            "attacker_role_id": None,
            "defender_role_id": None,
        }

        if mode_value == "attrition_manual":
            war["attacker_max_health"] = attacker_max
            war["defender_max_health"] = defender_max
            war["attacker_health"] = attacker_max
            war["defender_health"] = defender_max
        else:
            war["max_value"] = max_total

        wars.append(war)
        guild = interaction.guild
        if war["team_mentions"] and guild is not None:
            await self._ensure_role(guild, war, "attacker")
            await self._ensure_role(guild, war, "defender")
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
            attacker_next = self._next_participant(war, "attacker", consume=False)
            defender_next = self._next_participant(war, "defender", consume=False)
            embed.add_field(
                name=f"#{war.get('id')} — {_format_war_name(war)}",
                value=(
                    f"{_warbar_summary(war)}\n"
                    f"Mode: {_format_mode_label(war.get('mode'))} · "
                    f"Initiative: {war.get('initiative', 'attacker').title()} · "
                    f"Momentum: {_war_momentum_summary(int(war.get('momentum', 0)))}\n"
                    f"Next Attacker: {self._activation_display(war, 'attacker', attacker_next)} · "
                    f"Next Defender: {self._activation_display(war, 'defender', defender_next)}"
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
    @app_commands.choices(mode=MODE_CHOICES)
    async def war_update(
        self,
        interaction: discord.Interaction,
        war_id: int,
        name: Optional[str] = None,
        attacker: Optional[str] = None,
        defender: Optional[str] = None,
        theater: Optional[str] = None,
        mode: Optional[app_commands.Choice[str]] = None,
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
        rename_roles = False
        if name:
            war["name"] = name
            applied.append("name")
            rename_roles = True
        if attacker:
            war["attacker"] = attacker
            applied.append("attacker")
        if defender:
            war["defender"] = defender
            applied.append("defender")
        if theater:
            war["theater"] = theater
            applied.append("theater")
        if mode is not None:
            resolved_mode = _normalize_mode(
                mode.value if isinstance(mode, app_commands.Choice) else str(mode)
            )
            war["mode"] = resolved_mode
            self._apply_defaults(war)
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

        if rename_roles and war.get("team_mentions") and interaction.guild is not None:
            await self._rename_team_roles(interaction.guild, war)

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

    # === COMMAND: /war roster_add ===
    @app_commands.command(
        name="roster_add", description="Add a participant to a war roster."
    )
    @app_commands.guild_only()
    @app_commands.choices(side=SIDE_CHOICES)
    async def war_roster_add(
        self,
        interaction: discord.Interaction,
        war_id: int,
        side: app_commands.Choice[str],
        name: Optional[str] = None,
        member: Optional[discord.Member] = None,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        participant_name = name or (member.display_name if member else None)
        if not participant_name:
            await interaction.response.send_message(
                "Provide a participant name or select a Discord member.",
                ephemeral=True,
            )
            return

        self._add_participant(war, side.value, participant_name, member)

        guild = interaction.guild
        if war.get("team_mentions") and guild is not None and member is not None:
            await self._assign_member_to_role(guild, war, side.value, member)

        self._save(wars)

        await interaction.response.send_message(
            f"Added **{participant_name}** to the {side.name.lower()} roster for {_format_war_name(war)}.",
            ephemeral=True,
        )

    # === COMMAND: /war roster_remove ===
    @app_commands.command(
        name="roster_remove", description="Remove a participant from a war roster."
    )
    @app_commands.guild_only()
    @app_commands.choices(side=SIDE_CHOICES)
    async def war_roster_remove(
        self,
        interaction: discord.Interaction,
        war_id: int,
        side: app_commands.Choice[str],
        participant: int,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        roster = self._get_roster(war, side.value)
        if not roster:
            await interaction.response.send_message(
                f"No participants on the {side.name.lower()} roster.", ephemeral=True
            )
            return
        index = max(1, min(len(roster), participant)) - 1
        removed = self._remove_participant(war, side.value, index)

        guild = interaction.guild
        if war.get("team_mentions") and guild is not None:
            await self._remove_member_from_role(
                guild, war, side.value, removed.get("member_id")
            )

        self._save(wars)

        await interaction.response.send_message(
            f"Removed **{_format_participant_label(removed)}** from the {side.name.lower()} roster.",
            ephemeral=True,
        )

    # === COMMAND: /war roster_list ===
    @app_commands.command(
        name="roster_list", description="Show rosters for a war."
    )
    @app_commands.guild_only()
    async def war_roster_list(
        self, interaction: discord.Interaction, war_id: int
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        embed = discord.Embed(
            title=f"Roster — {_format_war_name(war)}",
            color=discord.Color.blurple(),
        )
        embed.add_field(
            name="Attacker Team",
            value=_format_roster_summary(war, "attacker"),
            inline=False,
        )
        embed.add_field(
            name="Defender Team",
            value=_format_roster_summary(war, "defender"),
            inline=False,
        )
        attacker_next = self._next_participant(war, "attacker", consume=False)
        defender_next = self._next_participant(war, "defender", consume=False)
        embed.add_field(
            name="Next Attacker",
            value=self._activation_display(war, "attacker", attacker_next),
            inline=True,
        )
        embed.add_field(
            name="Next Defender",
            value=self._activation_display(war, "defender", defender_next),
            inline=True,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === COMMAND: /war mention_mode ===
    @app_commands.command(
        name="mention_mode",
        description="Choose whether initiative mentions ping teams or individuals.",
    )
    @app_commands.guild_only()
    @app_commands.choices(mode=MENTION_MODE_CHOICES)
    async def war_mention_mode(
        self,
        interaction: discord.Interaction,
        war_id: int,
        mode: app_commands.Choice[str],
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "Guild context required to modify mention mode.",
                ephemeral=True,
            )
            return

        if mode.value == "team":
            war["team_mentions"] = True
            await self._ensure_role(guild, war, "attacker")
            await self._ensure_role(guild, war, "defender")
            await self._rename_team_roles(guild, war)
            await self._sync_roster_roles(guild, war, "attacker")
            await self._sync_roster_roles(guild, war, "defender")
            message = "Team role mentions enabled. Future initiative pings will @ the war roles."
        else:
            war["team_mentions"] = False
            await self._delete_role(guild, war, "attacker")
            await self._delete_role(guild, war, "defender")
            message = "Individual mentions enabled. Future initiative pings will @ roster members."

        self._save(wars)
        await interaction.response.send_message(message, ephemeral=True)

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

        mode_value = _normalize_mode(war.get("mode"))
        max_value = _get_max_value(war)

        if mode_value == "attrition_manual":
            view: discord.ui.View = AttritionResolutionView(
                interaction.user, _format_war_name(war)
            )
            prompt = (
                f"Resolving **{_format_war_name(war)}**.\n"
                "Choose an attrition action."
            )
        else:
            manual_mode = mode_value in {"pushpull_manual", "oneway_manual"}
            view = WarResolutionView(
                interaction.user,
                _format_war_name(war),
                manual_mode=manual_mode,
                mode=mode_value,
                max_value=max_value,
            )
            prompt = (
                f"Resolving **{_format_war_name(war)}**.\n"
                "Step 1 — choose the winning side or stalemate."
                if manual_mode
                else f"Resolving **{_format_war_name(war)}**.\n"
                "Step 1 — choose the winner."
            )

        await interaction.response.send_message(
            content=prompt,
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

        notes = result.get("notes", "")

        if mode_value == "attrition_manual":
            action = result.get("action")
            amount = abs(int(result.get("amount", 0)))

            attacker_max = max(1, int(war.get("attacker_max_health", 100)))
            defender_max = max(1, int(war.get("defender_max_health", 100)))
            attacker_hp = clamp(int(war.get("attacker_health", attacker_max)), 0, attacker_max)
            defender_hp = clamp(int(war.get("defender_health", defender_max)), 0, defender_max)

            embed_color = discord.Color.blue()
            if action == "damage_attacker":
                attacker_hp = clamp(attacker_hp - amount, 0, attacker_max)
                summary = f"Attacker takes {amount} damage."
                embed_color = discord.Color.red()
            elif action == "damage_defender":
                defender_hp = clamp(defender_hp - amount, 0, defender_max)
                summary = f"Defender takes {amount} damage."
                embed_color = discord.Color.red()
            elif action == "heal_attacker":
                attacker_hp = clamp(attacker_hp + amount, 0, attacker_max)
                summary = f"Attacker heals {amount}."
                embed_color = discord.Color.green()
            else:  # heal_defender
                defender_hp = clamp(defender_hp + amount, 0, defender_max)
                summary = f"Defender heals {amount}."
                embed_color = discord.Color.green()

            war["attacker_health"] = attacker_hp
            war["defender_health"] = defender_hp
            war["warbar"] = attacker_hp - defender_hp
            war["momentum"] = 0
            war["initiative"] = _flip_initiative(war.get("initiative", "attacker"))
            next_side = war["initiative"]
            next_participant = self._next_participant(war, next_side, consume=True)
            war["last_update"] = update_timestamp()
            war["notes"] = notes

            self._save(wars)

            embed = discord.Embed(
                title=f"📜 War Resolution — {_format_war_name(war)}",
                color=embed_color,
            )
            embed.description = _warbar_summary(war)
            embed.add_field(name="🎯 Action", value=summary, inline=False)
            embed.add_field(
                name="💚 Attacker HP",
                value=f"{attacker_hp}/{attacker_max}",
                inline=True,
            )
            embed.add_field(
                name="❤️ Defender HP",
                value=f"{defender_hp}/{defender_max}",
                inline=True,
            )
            if next_participant:
                embed.add_field(
                    name="Next Activation",
                    value=f"{next_side.title()}: {self._activation_display(war, next_side, next_participant)}",
                    inline=False,
                )
            embed.add_field(
                name="🎯 New Initiative", value=war["initiative"].title(), inline=True
            )
            embed.add_field(name="🕒 Updated", value=war["last_update"], inline=True)
            if notes:
                embed.add_field(name="🧾 Notes", value=notes, inline=False)

            allowed_mentions = self._allowed_mentions_for_participant(
                war, next_side, next_participant
            )
            await interaction.followup.send(
                embed=embed,
                allowed_mentions=allowed_mentions,
            )
            return

        previous_momentum = int(war.get("momentum", 0))
        last_winner = _derive_last_winner(previous_momentum)
        winner = result.get("winner")
        shift_value = int(result.get("shift", 0))

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

        current_bar = int(war.get("warbar", 0))
        if mode_value.startswith("oneway"):
            war["warbar"] = clamp(current_bar + warbar_delta, 0, max_value)
        else:
            war["warbar"] = clamp(current_bar + warbar_delta, -max_value, max_value)
        war["momentum"] = new_momentum
        war["initiative"] = _flip_initiative(war.get("initiative", "attacker"))
        next_side = war["initiative"]
        next_participant = self._next_participant(war, next_side, consume=True)
        war["last_update"] = update_timestamp()
        war["notes"] = notes

        self._save(wars)

        momentum_note = _war_momentum_summary(new_momentum)
        embed = discord.Embed(
            title=f"📜 War Resolution — {_format_war_name(war)}",
            color=embed_color,
        )
        embed.description = _warbar_summary(war)
        embed.add_field(name="🎲 Outcome", value=outcome_summary, inline=False)
        shift_field_name = "📈 WarBar Shift"
        if mode_value.startswith("oneway"):
            shift_field_name = "📈 Progress Shift"
        embed.add_field(
            name=shift_field_name,
            value=f"{warbar_delta:+d} (Momentum {momentum_note})",
            inline=False,
        )
        embed.add_field(
            name="🎯 New Initiative", value=war["initiative"].title(), inline=True
        )
        embed.add_field(name="🕒 Updated", value=war["last_update"], inline=True)
        if next_participant:
            embed.add_field(
                name="Next Activation",
                value=f"{next_side.title()}: {self._activation_display(war, next_side, next_participant)}",
                inline=False,
            )
        if notes:
            embed.add_field(name="🧾 Notes", value=notes, inline=False)

        allowed_mentions = self._allowed_mentions_for_participant(
            war, next_side, next_participant
        )
        await interaction.followup.send(
            embed=embed,
            allowed_mentions=allowed_mentions,
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
        next_side = war["initiative"]
        next_participant = self._next_participant(war, next_side, consume=True)
        war["last_update"] = update_timestamp()
        self._save(wars)

        lines = [
            f"Initiative flipped to **{war['initiative'].title()}** for {_format_war_name(war)}."
        ]
        mention_text = self._activation_display(war, next_side, next_participant)
        if mention_text != "N/A":
            lines.append(f"Next {next_side.title()}: {mention_text}")
        allowed_mentions = self._allowed_mentions_for_participant(
            war, next_side, next_participant
        )

        await interaction.response.send_message(
            "\n".join(lines),
            allowed_mentions=allowed_mentions,
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

        guild = interaction.guild
        if guild is not None:
            await self._delete_role(guild, war, "attacker")
            await self._delete_role(guild, war, "defender")

        wars = [existing for existing in wars if existing.get("id") != war_id]
        self._save(wars)
        # TODO: Implement war archival into wars_archive.json

        await interaction.response.send_message(
            f"War **{_format_war_name(war)}** has been removed from active tracking.",
            allowed_mentions=discord.AllowedMentions.none(),
        )

    @war_status.autocomplete("war_id")
    async def war_status_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_update.autocomplete("war_id")
    async def war_update_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_resolve.autocomplete("war_id")
    async def war_resolve_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_next.autocomplete("war_id")
    async def war_next_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_end.autocomplete("war_id")
    async def war_end_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_roster_add.autocomplete("war_id")
    async def war_roster_add_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_roster_remove.autocomplete("war_id")
    async def war_roster_remove_war_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_roster_list.autocomplete("war_id")
    async def war_roster_list_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_roster_remove.autocomplete("participant")
    async def war_roster_remove_participant_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        war_id = getattr(interaction.namespace, "war_id", None)
        side_value = getattr(interaction.namespace, "side", None)
        if war_id is None or side_value is None:
            return []
        try:
            war_id_int = int(war_id)
        except (TypeError, ValueError):
            return []
        side_key = side_value.value if isinstance(side_value, app_commands.Choice) else str(side_value)
        if side_key not in {"attacker", "defender"}:
            return []
        wars = self._load()
        war = find_war_by_id(wars, war_id_int)
        if war is None:
            return []
        return self._participant_choice_results(war, side_key, current)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WarCommands(bot))
