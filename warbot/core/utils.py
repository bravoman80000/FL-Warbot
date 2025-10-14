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
    """Render a 10-segment progress bar from 0 to max_value."""
    v = clamp(value, 0, max_value)
    segments = []
    total_segments = 10
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
