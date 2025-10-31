"""Utility helpers for war management logic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

# Emoji blocks for the war bar visual
DEFENDER_EMOJI: Final[str] = "🟥"
BACKGROUND_EMOJI: Final[str] = "🟧"
HIGHLIGHT_EMOJI: Final[str] = "🟨"
ATTACKER_EMOJI: Final[str] = "🟩"


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp ``value`` between ``minimum`` and ``maximum``."""
    return max(minimum, min(maximum, value))


def render_warbar(value: int, *, mode: str = "pushpull_auto", max_value: int = 100) -> str:
    """Render the war bar string for the requested mode."""
    normalized_mode = (mode or "pushpull_auto").lower()
    max_value = max(1, abs(int(max_value)))

    if normalized_mode.startswith("oneway"):
        return _render_oneway_bar(value, max_value)

    return _render_pushpull_bar(value, max_value)


def _render_pushpull_bar(value: int, max_value: int) -> str:
    """Render a 21-segment tug-of-war bar spanning -max_value to +max_value."""

    v = clamp(value, -max_value, max_value)
    ratio = v / max_value
    pivot = clamp(round(10 + ratio * 10), 0, 20)

    segments = []
    for idx in range(21):
        if idx == pivot:
            segments.append(HIGHLIGHT_EMOJI)
        elif idx < pivot:
            segments.append(ATTACKER_EMOJI)
        else:
            segments.append(DEFENDER_EMOJI)
    return "".join(segments)


def _render_oneway_bar(value: int, max_value: int) -> str:
    """Render a 20-segment progress bar from 0 to max_value."""
    v = clamp(value, 0, max_value)
    segments = []
    total_segments = 20
    step = max_value / total_segments
    for idx in range(total_segments):
        lower = step * idx
        upper = step * (idx + 1)
        if v >= upper:
            segments.append(ATTACKER_EMOJI)
        elif v > lower:
            segments.append(HIGHLIGHT_EMOJI)
        else:
            segments.append(DEFENDER_EMOJI)
    return "".join(segments)


def render_health_bar(current: int, maximum: int, *, side: str) -> str:
    """Render a health bar for attrition wars."""
    maximum = max(1, int(maximum))
    current = clamp(int(current), 0, maximum)

    fill = ATTACKER_EMOJI if side == "attacker" else DEFENDER_EMOJI
    empty = BACKGROUND_EMOJI

    segments = []
    total_segments = 10
    step = maximum / total_segments

    for idx in range(total_segments):
        threshold = step * (idx + 1)
        if current >= threshold:
            segments.append(fill)
        elif current > threshold - step:
            segments.append(HIGHLIGHT_EMOJI)
        else:
            segments.append(empty)

    return "".join(segments)


def calculate_momentum(prev: int, winner: str, last_winner: str | None) -> int:
    """Return the new momentum value for the winning side.

    Momentum is signed:
    - Positive values favour the attacker.
    - Negative values favour the defender.

    The absolute value is capped at 3 and increases by one
    when the same side wins successive resolutions.
    When the opposing side wins, momentum resets to ±1 for that side.
    Stalemate clears momentum to zero.
    """

    if winner not in {"attacker", "defender"}:
        return 0

    direction = 1 if winner == "attacker" else -1
    if last_winner == winner:
        magnitude = min(abs(prev) + 1, 3)
    else:
        magnitude = 1
    return direction * magnitude


def update_timestamp() -> str:
    """Return a UTC ISO 8601 timestamp without microseconds."""
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def update_dual_momentum(war: dict, winner: str) -> None:
    """Update both tactical and strategic momentum after a resolution.

    Tactical momentum: Short-term, ±1 to ±3, resets on opponent win
    Strategic momentum: Long-term, 0-10 per side, cumulative
    """
    prev_tactical = war.get("tactical_momentum", 0)
    last_winner = _derive_last_winner_from_momentum(prev_tactical)

    # Update tactical momentum (existing logic)
    if winner == "stalemate":
        war["tactical_momentum"] = 0
    elif winner == last_winner:
        # Same winner - increase magnitude (cap at 3)
        direction = 1 if winner == "attacker" else -1
        magnitude = min(abs(prev_tactical) + 1, 3)
        war["tactical_momentum"] = direction * magnitude
    else:
        # Different winner - reset to ±1
        war["tactical_momentum"] = 1 if winner == "attacker" else -1

    # Update strategic momentum (new cumulative system)
    if "strategic_momentum" not in war:
        war["strategic_momentum"] = {"attacker": 0, "defender": 0}

    if winner == "attacker":
        war["strategic_momentum"]["attacker"] = min(
            war["strategic_momentum"]["attacker"] + 1, 10
        )
        # Optional decay for opponent
        war["strategic_momentum"]["defender"] = max(
            war["strategic_momentum"]["defender"] - 1, 0
        )
    elif winner == "defender":
        war["strategic_momentum"]["defender"] = min(
            war["strategic_momentum"]["defender"] + 1, 10
        )
        war["strategic_momentum"]["attacker"] = max(
            war["strategic_momentum"]["attacker"] - 1, 0
        )
    # Stalemate: no change to strategic momentum


def _derive_last_winner_from_momentum(momentum: int) -> str | None:
    """Infer the last winning side from tactical momentum value."""
    if momentum > 0:
        return "attacker"
    if momentum < 0:
        return "defender"
    return None


def calculate_damage_multiplier(strategic_momentum: int) -> float:
    """Convert strategic momentum (0-10) to damage multiplier (1.0x-2.0x)."""
    return 1.0 + (strategic_momentum / 10)


def format_tactical_momentum(value: int) -> str:
    """Render tactical momentum with emoji indicators."""
    if value == 0:
        return "⚪ Neutral"

    side = "Attacker" if value > 0 else "Defender"
    magnitude = abs(value)
    lightning = "⚡" * magnitude

    return f"{lightning} {side} ({value:+d})"


def format_strategic_momentum(attacker_momentum: int, defender_momentum: int) -> str:
    """Render strategic momentum for both sides."""
    return f"Attacker {attacker_momentum}★ | Defender {defender_momentum}★"
