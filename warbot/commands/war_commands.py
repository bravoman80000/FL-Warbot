"""Slash commands for managing wars."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence, Tuple

import discord
from discord import app_commands
from discord.ext import commands

from ..core.data_manager import apply_war_defaults, find_war_by_id, load_wars, save_wars
from ..core.npc_ai import (
    ARCHETYPES,
    PERSONALITIES,
    TECH_LEVELS,
    apply_npc_config_to_war,
    choose_npc_actions,
    update_learning_data,
)
from ..core.npc_narratives import generate_npc_narrative
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


def _format_side_label(war: Dict[str, Any], side: str) -> str:
    """Return the user supplied team name with side context."""
    name = war.get(side) or side.title()
    role = "Attacker" if side == "attacker" else "Defender"
    return f"{name} ({role})"


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
            f"{_format_side_label(war, 'attacker')} HP: {attacker_bar} ({attacker_hp}/{attacker_max})\n"
            f"{_format_side_label(war, 'defender')} HP: {defender_bar} ({defender_hp}/{defender_max})"
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
    matchup = f"{_format_side_label(war, 'attacker')} vs {_format_side_label(war, 'defender')}"
    return f"{bar}\nWarBar: {value:+d}/{max_value} ({direction})\n{matchup}"


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


# === MAJOR OVERHAUL: Action Selection UI ===

MINOR_ACTION_CHOICES = [
    ("Prepare Attack (+1)", "prepare_attack"),
    ("Fortify Defense (-25% dmg)", "fortify_defense"),
    ("Sabotage Enemy (-1)", "sabotage"),
    ("Prepare Super Unit", "prepare_super_unit"),
    ("Heal (Attrition)", "heal"),
    ("Research Super Unit", "research_super_unit"),
]


class ActionSelectionModal(discord.ui.Modal, title="War Resolution - Enter Rolls"):
    """Modal for entering manual dice rolls."""

    attacker_roll_input = discord.ui.TextInput(
        label="Attacker Roll (leave blank for auto)",
        placeholder="1-20 or blank",
        required=False,
        max_length=2,
    )
    defender_roll_input = discord.ui.TextInput(
        label="Defender Roll (leave blank for auto)",
        placeholder="1-20 or blank",
        required=False,
        max_length=2,
    )

    def __init__(self, parent_view: "GMActionSelectionView") -> None:
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction) -> None:
        # Parse rolls
        attacker_roll = None
        defender_roll = None

        if self.attacker_roll_input.value.strip():
            try:
                attacker_roll = int(self.attacker_roll_input.value.strip())
                if not (1 <= attacker_roll <= 20):
                    await interaction.response.send_message(
                        "Attacker roll must be 1-20!", ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "Invalid attacker roll!", ephemeral=True
                )
                return

        if self.defender_roll_input.value.strip():
            try:
                defender_roll = int(self.defender_roll_input.value.strip())
                if not (1 <= defender_roll <= 20):
                    await interaction.response.send_message(
                        "Defender roll must be 1-20!", ephemeral=True
                    )
                    return
            except ValueError:
                await interaction.response.send_message(
                    "Invalid defender roll!", ephemeral=True
                )
                return

        self.parent_view.attacker_roll = attacker_roll
        self.parent_view.defender_roll = defender_roll
        self.parent_view.rolls_entered = True

        await interaction.response.defer()
        await self.parent_view.proceed_to_resolution()


class MinorActionSelect(discord.ui.Select):
    """Dropdown for selecting minor action."""

    def __init__(self, side: str, parent_view: "GMActionSelectionView") -> None:
        options = [
            discord.SelectOption(label=label, value=value)
            for label, value in MINOR_ACTION_CHOICES
        ]
        super().__init__(
            placeholder=f"{side} Minor Action",
            options=options,
            custom_id=f"minor_{side.lower()}",
        )
        self.side = side
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.side == "Attacker":
            self.parent_view.attacker_minor = self.values[0]
        else:
            self.parent_view.defender_minor = self.values[0]

        await interaction.response.defer()
        await self.parent_view.check_if_ready()


class MainActionButton(discord.ui.Button):
    """Button for selecting main action."""

    def __init__(
        self, label: str, action: str, side: str, parent_view: "GMActionSelectionView"
    ) -> None:
        super().__init__(label=f"{side}: {label}", style=discord.ButtonStyle.primary)
        self.action = action
        self.side = side
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction) -> None:
        if self.side == "Attacker":
            self.parent_view.attacker_main = self.action
        else:
            self.parent_view.defender_main = self.action

        await interaction.response.defer()
        await self.parent_view.check_if_ready()


class GMActionSelectionView(discord.ui.View):
    """UI for GM to select actions for both sides in a resolution."""

    def __init__(self, war: Dict[str, Any], user: discord.abc.User) -> None:
        super().__init__(timeout=300)
        self.war = war
        self.user = user
        self.message: Optional[discord.Message] = None

        # Action selections
        self.attacker_main: Optional[str] = None
        self.defender_main: Optional[str] = None
        self.attacker_minor: Optional[str] = None
        self.defender_minor: Optional[str] = None

        # Roll results
        self.attacker_roll: Optional[int] = None
        self.defender_roll: Optional[int] = None
        self.rolls_entered = False

        # Result
        self.result: Optional[Dict[str, Any]] = None
        self._finished = asyncio.Event()

        # Build UI
        self._build_ui()

    def _build_ui(self) -> None:
        """Build the action selection UI."""
        # Main action buttons
        self.add_item(MainActionButton("Attack", "attack", "Attacker", self))
        self.add_item(MainActionButton("Defend", "defend", "Attacker", self))
        self.add_item(MainActionButton("Super Unit", "super_unit", "Attacker", self))

        self.add_item(MainActionButton("Attack", "attack", "Defender", self))
        self.add_item(MainActionButton("Defend", "defend", "Defender", self))
        self.add_item(MainActionButton("Super Unit", "super_unit", "Defender", self))

        # Minor action dropdowns
        self.add_item(MinorActionSelect("Attacker", self))
        self.add_item(MinorActionSelect("Defender", self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user.id:
            await interaction.response.send_message(
                "Only the command invoker can use this view.", ephemeral=True
            )
            return False
        return True

    async def check_if_ready(self) -> None:
        """Check if all actions are selected and prompt for rolls."""
        if (
            self.attacker_main
            and self.defender_main
            and self.attacker_minor
            and self.defender_minor
            and not self.rolls_entered
        ):
            # All actions selected, show modal for rolls
            if self.message:
                await self.message.edit(
                    content="✅ Actions selected! Enter rolls (or leave blank for auto)...",
                    view=self,
                )

    async def proceed_to_resolution(self) -> None:
        """After rolls are entered, proceed with resolution."""
        # Store result
        self.result = {
            "attacker_main": self.attacker_main,
            "attacker_minor": self.attacker_minor,
            "attacker_roll": self.attacker_roll,
            "defender_main": self.defender_main,
            "defender_minor": self.defender_minor,
            "defender_roll": self.defender_roll,
        }

        self.disable_all()
        if self.message:
            await self.message.edit(
                content="🎲 Resolving combat...",
                view=self,
            )

        self._finished.set()

    def disable_all(self) -> None:
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True

    async def on_timeout(self) -> None:
        self.disable_all()
        if self.message:
            await self.message.edit(
                content="⏱️ Action selection timed out.", view=self
            )

    async def wait_for_result(self) -> Optional[Dict[str, Any]]:
        """Wait for the user to complete action selection."""
        await self._finished.wait()
        return self.result

    @discord.ui.button(label="Enter Rolls & Resolve", style=discord.ButtonStyle.success, row=4)
    async def submit_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        """Submit button to enter rolls and resolve."""
        if not (
            self.attacker_main
            and self.defender_main
            and self.attacker_minor
            and self.defender_minor
        ):
            await interaction.response.send_message(
                "❌ Please select all actions first!", ephemeral=True
            )
            return

        modal = ActionSelectionModal(self)
        await interaction.response.send_modal(modal)


# === END MAJOR OVERHAUL ===


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
            # Apply existing defaults
            if self._apply_defaults(war):
                mutated = True
            # Apply new Major Overhaul defaults
            if apply_war_defaults(war):
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

    async def _auto_resolve_player_war(
        self, war: Dict[str, Any], wars: List[Dict[str, Any]]
    ) -> None:
        """Auto-resolve a player-driven war when both sides have submitted actions."""
        from ..core.combat import (
            calculate_damage_from_margin,
            calculate_modifiers,
            cleanup_expired_modifiers,
        )
        from ..core.utils import (
            format_strategic_momentum,
            format_tactical_momentum,
            render_warbar,
            update_dual_momentum,
        )
        import random

        attacker_action = war["pending_actions"]["attacker"]
        defender_action = war["pending_actions"]["defender"]

        # Calculate modifiers
        attacker_mods, attacker_total = calculate_modifiers(
            war, "attacker", attacker_action["main"], attacker_action["minor"]
        )
        defender_mods, defender_total = calculate_modifiers(
            war, "defender", defender_action["main"], defender_action["minor"]
        )

        # Handle sabotage
        if attacker_action["minor"] == "sabotage":
            defender_mods.append(("Enemy Sabotage", -1))
            defender_total -= 1
        if defender_action["minor"] == "sabotage":
            attacker_mods.append(("Enemy Sabotage", -1))
            attacker_total -= 1

        # Roll dice
        attacker_roll = attacker_action["roll"] or random.randint(1, 20)
        defender_roll = defender_action["roll"] or random.randint(1, 20)

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
        if attacker_action["main"] == "defend" and winner == "defender":
            damage = int(damage * 0.5)
        elif defender_action["main"] == "defend" and winner == "attacker":
            damage = int(damage * 0.5)

        # Apply damage to warbar
        mode_value = _normalize_mode(war.get("mode"))
        if winner == "attacker":
            war["warbar"] = min(war["warbar"] + damage, _get_max_value(war))
        elif winner == "defender":
            war["warbar"] = max(war["warbar"] - damage, -_get_max_value(war))

        # Update dual-track momentum
        update_dual_momentum(war, winner)

        # Clean up expired modifiers
        cleanup_expired_modifiers(war)

        # Update NPC learning data if applicable
        npc_config = war.get("npc_config", {})
        if npc_config.get("enabled", False):
            npc_side = npc_config.get("side")
            if npc_side:
                # Determine NPC outcome
                if winner == "stalemate":
                    npc_outcome = "stalemate"
                elif winner == npc_side:
                    npc_outcome = "win"
                else:
                    npc_outcome = "loss"

                # Calculate margin from NPC perspective
                npc_margin = abs(difference)
                if npc_outcome == "loss":
                    npc_margin = -npc_margin

                # Update learning data
                learning_data = npc_config.get("learning_data", {})
                updated_learning = update_learning_data(learning_data, npc_outcome, npc_margin)
                war["npc_config"]["learning_data"] = updated_learning

        # Update war state
        war["initiative"] = _flip_initiative(war.get("initiative", "attacker"))
        war["last_update"] = update_timestamp()
        war["last_resolution_time"] = update_timestamp()

        # Clear pending actions
        war["pending_actions"] = {"attacker": None, "defender": None}

        self._save(wars)

        # Build result embed
        embed = discord.Embed(
            title=f"⚔️ WAR RESOLUTION: {_format_war_name(war)}",
            color=discord.Color.gold(),
        )

        # Narrative links
        if not attacker_action.get("is_npc"):
            embed.add_field(
                name="📖 Attacker Narrative",
                value=f"[Read Post]({attacker_action['narrative_link']})",
                inline=True,
            )
        else:
            embed.add_field(
                name="📖 Attacker Narrative (NPC)",
                value=attacker_action.get("narrative_text", "NPC action"),
                inline=True,
            )

        if not defender_action.get("is_npc"):
            embed.add_field(
                name="📖 Defender Narrative",
                value=f"[Read Post]({defender_action['narrative_link']})",
                inline=True,
            )
        else:
            embed.add_field(
                name="📖 Defender Narrative (NPC)",
                value=defender_action.get("narrative_text", "NPC action"),
                inline=True,
            )

        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # Roll results
        attacker_mods_str = "\n".join(f"{name}: {val:+d}" for name, val in attacker_mods)
        defender_mods_str = "\n".join(f"{name}: {val:+d}" for name, val in defender_mods)

        embed.add_field(
            name="🎲 Attacker Roll",
            value=f"Roll: {attacker_roll}\n{attacker_mods_str}\n**Total: {attacker_result}**",
            inline=True,
        )
        embed.add_field(
            name="🎲 Defender Roll",
            value=f"Roll: {defender_roll}\n{defender_mods_str}\n**Total: {defender_result}**",
            inline=True,
        )
        embed.add_field(name="\u200b", value="\u200b", inline=False)

        # Result
        if winner == "stalemate":
            result_text = "🤝 **Stalemate!**"
        else:
            result_text = f"🏆 **{winner.title()} Victory!**\nDamage: {damage} warbar"

        embed.add_field(name="Result", value=result_text, inline=False)

        # Warbar
        embed.add_field(
            name="War Progress",
            value=render_warbar(war["warbar"], mode=mode_value, max_value=_get_max_value(war))
            + f"\n{war['warbar']:+d}/{_get_max_value(war)}",
            inline=False,
        )

        # Momentum
        embed.add_field(
            name="Momentum",
            value=f"Tactical: {format_tactical_momentum(war.get('tactical_momentum', 0))}\n"
            f"Strategic: {format_strategic_momentum(war['strategic_momentum']['attacker'], war['strategic_momentum']['defender'])}",
            inline=False,
        )

        # Send to war channel
        channel_id = war.get("channel_id")
        if channel_id:
            try:
                channel = await self.bot.fetch_channel(int(channel_id))
                if isinstance(channel, discord.abc.Messageable):
                    await channel.send(embed=embed)
            except discord.HTTPException:
                pass

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
    @app_commands.choices(mode=MODE_CHOICES, mention_mode=MENTION_MODE_CHOICES)
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
        mention_mode: Optional[app_commands.Choice[str]] = None,
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

        guild = interaction.guild

        if mention_mode is not None:
            if guild is None:
                await interaction.response.send_message(
                    "Guild context required to alter mention mode.",
                    ephemeral=True,
                )
                return
            if mention_mode.value == "team":
                war["team_mentions"] = True
                await self._ensure_role(guild, war, "attacker")
                await self._ensure_role(guild, war, "defender")
                await self._rename_team_roles(guild, war)
                await self._sync_roster_roles(guild, war, "attacker")
                await self._sync_roster_roles(guild, war, "defender")
                applied.append("mention_mode(team)")
            else:
                war["team_mentions"] = False
                await self._delete_role(guild, war, "attacker")
                await self._delete_role(guild, war, "defender")
                applied.append("mention_mode(individual)")

        if not applied:
            await interaction.response.send_message(
                "No updates supplied. Provide at least one field to change.",
                ephemeral=True,
            )
            return

        if rename_roles and war.get("team_mentions") and guild is not None:
            await self._rename_team_roles(guild, war)

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

        # Check if player-driven mode
        if war.get("resolution_mode") == "player_driven":
            await interaction.response.send_message(
                "⚠️ This war is in player-driven mode. Players use `/war action` instead.",
                ephemeral=True
            )
            return

        # NEW: Check if using Major Overhaul system (has stats configured)
        has_stats = (
            war.get("stats")
            and any(war["stats"]["attacker"].values())
            or any(war["stats"]["defender"].values())
        )

        if has_stats:
            # Use new GM Action Selection system
            from ..core.combat import (
                calculate_damage_from_margin,
                calculate_modifiers,
                cleanup_expired_modifiers,
            )
            from ..core.utils import update_dual_momentum
            import random

            view = GMActionSelectionView(war, interaction.user)
            await interaction.response.send_message(
                content=f"🎮 Resolving **{_format_war_name(war)}** (Major Overhaul System)\n"
                "Select actions for both sides:",
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

            # Calculate modifiers for both sides
            attacker_mods, attacker_total = calculate_modifiers(
                war, "attacker", result["attacker_main"], result["attacker_minor"]
            )
            defender_mods, defender_total = calculate_modifiers(
                war, "defender", result["defender_main"], result["defender_minor"]
            )

            # Handle sabotage
            if result["attacker_minor"] == "sabotage":
                defender_mods.append(("Enemy Sabotage", -1))
                defender_total -= 1
            if result["defender_minor"] == "sabotage":
                attacker_mods.append(("Enemy Sabotage", -1))
                attacker_total -= 1

            # Roll dice
            attacker_roll = result["attacker_roll"] or random.randint(1, 20)
            defender_roll = result["defender_roll"] or random.randint(1, 20)

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
            if result.get("attacker_main") == "defend" and winner == "defender":
                damage = int(damage * 0.5)
            elif result.get("defender_main") == "defend" and winner == "attacker":
                damage = int(damage * 0.5)

            # Apply damage to warbar
            mode_value = _normalize_mode(war.get("mode"))
            if winner == "attacker":
                war["warbar"] = min(war["warbar"] + damage, _get_max_value(war))
            elif winner == "defender":
                war["warbar"] = max(war["warbar"] - damage, -_get_max_value(war))

            # Update dual-track momentum
            update_dual_momentum(war, winner)

            # Clean up expired modifiers
            cleanup_expired_modifiers(war)

            # Update war state
            war["initiative"] = _flip_initiative(war.get("initiative", "attacker"))
            war["last_update"] = update_timestamp()

            self._save(wars)

            # Build result embed
            from ..core.utils import (
                format_strategic_momentum,
                format_tactical_momentum,
                render_warbar,
            )

            embed = discord.Embed(
                title=f"⚔️ War Resolution — {_format_war_name(war)}",
                color=discord.Color.gold(),
            )

            # Actions taken
            embed.add_field(
                name="🎯 Attacker Actions",
                value=f"Main: {result['attacker_main'].title()}\n"
                f"Minor: {result['attacker_minor'].replace('_', ' ').title()}",
                inline=True,
            )
            embed.add_field(
                name="🎯 Defender Actions",
                value=f"Main: {result['defender_main'].title()}\n"
                f"Minor: {result['defender_minor'].replace('_', ' ').title()}",
                inline=True,
            )
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # Roll results
            attacker_mods_str = "\n".join(f"{name}: {val:+d}" for name, val in attacker_mods)
            defender_mods_str = "\n".join(f"{name}: {val:+d}" for name, val in defender_mods)

            embed.add_field(
                name=f"🎲 Attacker Roll",
                value=f"Roll: {attacker_roll}\n{attacker_mods_str}\n**Total: {attacker_result}**",
                inline=True,
            )
            embed.add_field(
                name=f"🎲 Defender Roll",
                value=f"Roll: {defender_roll}\n{defender_mods_str}\n**Total: {defender_result}**",
                inline=True,
            )
            embed.add_field(name="\u200b", value="\u200b", inline=False)

            # Result
            if winner == "stalemate":
                result_text = "🤝 **Stalemate!**"
            else:
                result_text = f"🏆 **{winner.title()} Victory!**\nDamage: {damage} warbar"

            embed.add_field(name="Result", value=result_text, inline=False)

            # Warbar
            embed.add_field(
                name="War Progress",
                value=render_warbar(war["warbar"], mode=mode_value, max_value=_get_max_value(war)) +
                      f"\n{war['warbar']:+d}/{_get_max_value(war)}",
                inline=False,
            )

            # Momentum
            embed.add_field(
                name="Momentum",
                value=f"Tactical: {format_tactical_momentum(war.get('tactical_momentum', 0))}\n"
                      f"Strategic: {format_strategic_momentum(war['strategic_momentum']['attacker'], war['strategic_momentum']['defender'])}",
                inline=False,
            )

            # Send to war channel
            channel_id = war.get("channel_id")
            if channel_id:
                try:
                    channel = await self.bot.fetch_channel(int(channel_id))
                    if isinstance(channel, discord.abc.Messageable):
                        await channel.send(embed=embed)
                except discord.HTTPException:
                    pass

            await interaction.followup.send("✅ Resolution complete!", embed=embed, ephemeral=True)
            return

        # EXISTING: Legacy system for wars without stats
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

    # === NEW COMMANDS: MAJOR OVERHAUL ===

    @app_commands.command(
        name="action",
        description="Submit your war action with narrative (player-driven wars).",
    )
    @app_commands.guild_only()
    @app_commands.choices(main=[
        app_commands.Choice(name="Attack", value="attack"),
        app_commands.Choice(name="Defend", value="defend"),
        app_commands.Choice(name="Super Unit", value="super_unit"),
    ])
    @app_commands.choices(minor=[
        app_commands.Choice(name=label, value=value)
        for label, value in MINOR_ACTION_CHOICES
    ])
    async def war_action(
        self,
        interaction: discord.Interaction,
        war_id: int,
        main: app_commands.Choice[str],
        minor: app_commands.Choice[str],
        narrative_link: str,
        roll: Optional[int] = None,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        # Check if war is player-driven
        if war.get("resolution_mode") != "player_driven":
            await interaction.response.send_message(
                "⚠️ This war is GM-driven. GMs use `/war resolve` instead.\n"
                f"To enable player-driven mode, use `/war set_mode war_id:{war_id} mode:Player-Driven`",
                ephemeral=True,
            )
            return

        # Check cooldown
        from datetime import datetime, timedelta, timezone

        last_resolution = war.get("last_resolution_time")
        cooldown_hours = war.get("resolution_cooldown_hours", 12)

        if last_resolution:
            try:
                last_time = datetime.fromisoformat(last_resolution)
                if last_time.tzinfo is None:
                    last_time = last_time.replace(tzinfo=timezone.utc)

                now = datetime.now(timezone.utc)
                time_since = (now - last_time).total_seconds() / 3600

                if time_since < cooldown_hours:
                    remaining = cooldown_hours - time_since
                    await interaction.response.send_message(
                        f"⏳ Cooldown active. Next resolution available in {remaining:.1f} hours.",
                        ephemeral=True,
                    )
                    return
            except (ValueError, TypeError):
                pass

        # Validate narrative link
        try:
            # Extract message ID from link
            # Discord message links: https://discord.com/channels/guild_id/channel_id/message_id
            parts = narrative_link.split("/")
            if len(parts) < 3:
                raise ValueError("Invalid link format")

            message_id = int(parts[-1])
            channel_id = int(parts[-2])

            # Fetch the message
            channel = await self.bot.fetch_channel(channel_id)
            if not isinstance(channel, discord.abc.Messageable):
                raise ValueError("Channel not messageable")

            message = await channel.fetch_message(message_id)

            # Check message length
            if len(message.content) < 100:
                await interaction.response.send_message(
                    f"❌ Narrative too short! Your post must be at least 100 characters.\n"
                    f"Current length: {len(message.content)} characters.",
                    ephemeral=True,
                )
                return

        except (ValueError, IndexError, discord.HTTPException) as e:
            await interaction.response.send_message(
                f"❌ Invalid narrative link! Please provide a Discord message link.\n"
                f"Right-click a message → Copy Message Link\n"
                f"Error: {str(e)}",
                ephemeral=True,
            )
            return

        # Determine player's side
        player_side = None
        for side in ("attacker", "defender"):
            roster = war.get(f"{side}_roster", [])
            for participant in roster:
                if participant.get("member_id") == interaction.user.id:
                    player_side = side
                    break
            if player_side:
                break

        if not player_side:
            await interaction.response.send_message(
                "❌ You are not a participant in this war!",
                ephemeral=True,
            )
            return

        # Check if player already submitted
        if war["pending_actions"].get(player_side) is not None:
            await interaction.response.send_message(
                "❌ You've already submitted an action for this round!",
                ephemeral=True,
            )
            return

        # Validate roll if provided
        if roll is not None and not (1 <= roll <= 20):
            await interaction.response.send_message(
                "❌ Roll must be between 1 and 20!", ephemeral=True
            )
            return

        # Store action
        war["pending_actions"][player_side] = {
            "main": main.value,
            "minor": minor.value,
            "narrative_link": narrative_link,
            "roll": roll,
            "player_id": interaction.user.id,
            "is_npc": False,
        }

        self._save(wars)

        # Check if both sides have submitted
        opponent_side = "defender" if player_side == "attacker" else "attacker"

        # Check if opponent is NPC-controlled
        npc_config = war.get("npc_config", {})
        is_npc_opponent = (
            npc_config.get("enabled", False) and npc_config.get("side") == opponent_side
        )

        # If opponent is NPC, auto-generate their action
        if is_npc_opponent and war["pending_actions"].get(opponent_side) is None:
            import random

            # Get NPC learning data
            learning_data = npc_config.get("learning_data", {})

            # Choose NPC actions
            npc_main, npc_minor = choose_npc_actions(
                war,
                opponent_side,
                npc_config.get("archetype", "nato"),
                npc_config.get("personality", "balanced"),
                learning_data,
            )

            # Generate narrative
            npc_narrative = generate_npc_narrative(
                war,
                opponent_side,
                npc_main,
                npc_minor,
                npc_config.get("archetype", "nato"),
                npc_config.get("tech_level", "modern"),
                npc_config.get("personality", "balanced"),
            )

            # Store NPC action
            war["pending_actions"][opponent_side] = {
                "main": npc_main,
                "minor": npc_minor,
                "narrative_link": None,
                "narrative_text": npc_narrative,
                "roll": random.randint(1, 20),
                "player_id": None,
                "is_npc": True,
            }

            self._save(wars)

        if war["pending_actions"].get(opponent_side) is not None:
            # Both sides submitted - auto-resolve!
            await interaction.response.send_message(
                "✅ Action submitted! Both sides ready - resolving now...",
                ephemeral=True,
            )

            await self._auto_resolve_player_war(war, wars)
        else:
            await interaction.response.send_message(
                f"✅ Action submitted! Waiting for {opponent_side.title()}...",
                ephemeral=True,
            )

    @app_commands.command(
        name="set_stats",
        description="Set faction stats for a war side (exosphere/naval/military).",
    )
    @app_commands.guild_only()
    @app_commands.choices(side=SIDE_CHOICES)
    async def war_set_stats(
        self,
        interaction: discord.Interaction,
        war_id: int,
        side: app_commands.Choice[str],
        exosphere: int,
        naval: int,
        military: int,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        side_key = side.value
        war["stats"][side_key] = {
            "exosphere": exosphere,
            "naval": naval,
            "military": military
        }

        self._save(wars)

        await interaction.response.send_message(
            f"✅ Stats updated for {side.name} in War #{war_id}:\n"
            f"  Exosphere: {exosphere}\n"
            f"  Naval: {naval}\n"
            f"  Military: {military}",
            ephemeral=True
        )

    @app_commands.command(
        name="set_theater",
        description="Set war theater (cosmetic label for where the war is fought).",
    )
    @app_commands.guild_only()
    @app_commands.choices(theater=[
        app_commands.Choice(name="Space", value="space"),
        app_commands.Choice(name="Naval", value="naval"),
        app_commands.Choice(name="Land", value="land"),
        app_commands.Choice(name="Combined Arms", value="combined"),
    ])
    async def war_set_theater(
        self,
        interaction: discord.Interaction,
        war_id: int,
        theater: app_commands.Choice[str],
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        war["theater"] = theater.value
        self._save(wars)

        await interaction.response.send_message(
            f"✅ Theater set to **{theater.name}** for War #{war_id}.",
            ephemeral=True
        )

    @app_commands.command(
        name="add_modifier",
        description="Add a combat modifier to a war side.",
    )
    @app_commands.guild_only()
    @app_commands.choices(side=SIDE_CHOICES)
    @app_commands.choices(duration=[
        app_commands.Choice(name="Permanent", value="permanent"),
        app_commands.Choice(name="Next Resolution", value="next_resolution"),
        app_commands.Choice(name="2 Turns", value="2_turns"),
        app_commands.Choice(name="3 Turns", value="3_turns"),
        app_commands.Choice(name="5 Turns", value="5_turns"),
    ])
    async def war_add_modifier(
        self,
        interaction: discord.Interaction,
        war_id: int,
        side: app_commands.Choice[str],
        name: str,
        value: int,
        duration: app_commands.Choice[str] = None,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        side_key = side.value
        duration_value = duration.value if duration else "permanent"

        modifier = {
            "name": name,
            "value": value,
            "duration": duration_value,
        }

        war["modifiers"][side_key].append(modifier)
        self._save(wars)

        await interaction.response.send_message(
            f"✅ Modifier added to {side.name} in War #{war_id}:\n"
            f"  **{name}**: {value:+d} ({duration_value})",
            ephemeral=True
        )

    @app_commands.command(
        name="remove_modifier",
        description="Remove a combat modifier from a war side by name.",
    )
    @app_commands.guild_only()
    @app_commands.choices(side=SIDE_CHOICES)
    async def war_remove_modifier(
        self,
        interaction: discord.Interaction,
        war_id: int,
        side: app_commands.Choice[str],
        name: str,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        side_key = side.value
        modifiers = war["modifiers"][side_key]

        # Find and remove modifier by name
        original_count = len(modifiers)
        war["modifiers"][side_key] = [m for m in modifiers if m["name"] != name]
        removed_count = original_count - len(war["modifiers"][side_key])

        if removed_count == 0:
            await interaction.response.send_message(
                f"❌ No modifier named \"{name}\" found for {side.name}.",
                ephemeral=True
            )
            return

        self._save(wars)

        await interaction.response.send_message(
            f"✅ Removed {removed_count} modifier(s) named \"{name}\" from {side.name} in War #{war_id}.",
            ephemeral=True
        )

    @app_commands.command(
        name="set_mode",
        description="Toggle between GM-driven and player-driven war resolution.",
    )
    @app_commands.guild_only()
    @app_commands.choices(mode=[
        app_commands.Choice(name="GM-Driven (Traditional)", value="gm_driven"),
        app_commands.Choice(name="Player-Driven (Automatic)", value="player_driven"),
    ])
    async def war_set_mode(
        self,
        interaction: discord.Interaction,
        war_id: int,
        mode: app_commands.Choice[str],
        cooldown_hours: int = 12,
    ) -> None:
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        war["resolution_mode"] = mode.value
        war["resolution_cooldown_hours"] = cooldown_hours

        self._save(wars)

        mode_description = {
            "gm_driven": "Traditional GM resolution using `/war resolve`",
            "player_driven": f"Player-driven resolution using `/war action` (cooldown: {cooldown_hours}h)"
        }

        await interaction.response.send_message(
            f"✅ War #{war_id} resolution mode set to **{mode.name}**.\n"
            f"{mode_description[mode.value]}",
            ephemeral=True
        )

    @app_commands.command(
        name="set_npc",
        description="Configure an NPC opponent for PvE war.",
    )
    @app_commands.guild_only()
    @app_commands.choices(side=SIDE_CHOICES)
    @app_commands.choices(archetype=[
        app_commands.Choice(name=v["name"], value=k)
        for k, v in ARCHETYPES.items()
    ])
    @app_commands.choices(tech_level=[
        app_commands.Choice(name=v["name"], value=k)
        for k, v in TECH_LEVELS.items()
    ])
    @app_commands.choices(personality=[
        app_commands.Choice(name=v["name"], value=k)
        for k, v in PERSONALITIES.items()
    ])
    async def war_set_npc(
        self,
        interaction: discord.Interaction,
        war_id: int,
        side: app_commands.Choice[str],
        archetype: app_commands.Choice[str],
        tech_level: app_commands.Choice[str],
        personality: app_commands.Choice[str],
    ) -> None:
        """Configure an NPC opponent for a war side.

        This enables PvE mode where the NPC will automatically respond to player actions.
        """
        wars = self._load()
        war = find_war_by_id(wars, war_id)
        if war is None:
            await interaction.response.send_message(
                f"War with ID {war_id} not found.", ephemeral=True
            )
            return

        # Apply NPC configuration
        apply_npc_config_to_war(
            war,
            side.value,
            archetype.value,
            tech_level.value,
            personality.value
        )

        self._save(wars)

        # Build info embed
        archetype_info = ARCHETYPES[archetype.value]
        tech_info = TECH_LEVELS[tech_level.value]
        personality_info = PERSONALITIES[personality.value]

        embed = discord.Embed(
            title=f"🤖 NPC Configured for War #{war_id}",
            description=f"**{side.name}** is now controlled by AI",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Archetype",
            value=f"**{archetype_info['name']}**\n{archetype_info['description']}",
            inline=False
        )

        embed.add_field(
            name="Tech Level",
            value=f"**{tech_info['name']}** ({tech_info['stat_multiplier']}x)\n{tech_info['description']}",
            inline=False
        )

        embed.add_field(
            name="Personality",
            value=f"**{personality_info['name']}**\n{personality_info['description']}",
            inline=False
        )

        # Show generated stats
        stats = war["stats"][side.value]
        embed.add_field(
            name="Generated Stats",
            value=f"Exosphere: {stats['exosphere']}\nNaval: {stats['naval']}\nMilitary: {stats['military']}",
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # === AUTOCOMPLETE PROVIDERS ===

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

    @war_mention_mode.autocomplete("war_id")
    async def war_mention_mode_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_action.autocomplete("war_id")
    async def war_action_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_set_stats.autocomplete("war_id")
    async def war_set_stats_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_set_theater.autocomplete("war_id")
    async def war_set_theater_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_add_modifier.autocomplete("war_id")
    async def war_add_modifier_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_remove_modifier.autocomplete("war_id")
    async def war_remove_modifier_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_set_mode.autocomplete("war_id")
    async def war_set_mode_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)

    @war_set_npc.autocomplete("war_id")
    async def war_set_npc_autocomplete(
        self, interaction: discord.Interaction, current: str
    ) -> List[app_commands.Choice[int]]:
        return self._war_choice_results(current)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(WarCommands(bot))
