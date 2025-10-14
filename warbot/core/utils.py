"""Utility helpers for war management logic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Final

# Emoji blocks for the war bar visual
NEGATIVE_EMOJI: Final[str] = "🟥"
WARNING_EMOJI: Final[str] = "🟧"
NEUTRAL_EMOJI: Final[str] = "🟨"
POSITIVE_EMOJI: Final[str] = "🟩"


def clamp(value: int, minimum: int, maximum: int) -> int:
    """Clamp ``value`` between ``minimum`` and ``maximum``."""
    return max(minimum, min(maximum, value))


def render_warbar(value: int) -> str:
    """Render the war bar as a 10-segment emoji string."""
    value = clamp(value, -100, 100)
    segments = []
    for index in range(10):
        threshold = 100 - 20 * (index + 1)
        diff = value - threshold
        if diff >= 10:
            segments.append(POSITIVE_EMOJI)
        elif diff >= -10:
            segments.append(NEUTRAL_EMOJI)
        elif diff >= -30:
            segments.append(WARNING_EMOJI)
        else:
            segments.append(NEGATIVE_EMOJI)
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
