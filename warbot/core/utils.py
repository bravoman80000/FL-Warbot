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


def render_warbar(value: int, *, mode: str = "pushpull") -> str:
    """Render the war bar string for the requested mode."""
    normalized_mode = (mode or "pushpull").lower()
    if normalized_mode == "oneway":
        return _render_oneway_bar(value)
    return _render_pushpull_bar(value)


def _render_pushpull_bar(value: int) -> str:
    """Render a 21-segment tug-of-war bar spanning -100 to +100.

    The bar always shows the attacker on the left (green) and defender
    on the right (red). The boundary between them is highlighted.
    """

    v = clamp(value, -100, 100)
    # Determine which cell is the contested boundary.
    offset = round(v / 10)
    pivot = clamp(10 + offset, 0, 20)

    segments = []
    for idx in range(21):
        if idx == pivot:
            segments.append(HIGHLIGHT_EMOJI)
        elif idx < pivot:
            segments.append(ATTACKER_EMOJI)
        else:
            segments.append(DEFENDER_EMOJI)
    return "".join(segments)


def _render_oneway_bar(value: int) -> str:
    """Render an 11-segment progress bar from 0 to 100."""
    v = clamp(value, 0, 100)
    segments = []
    for idx in range(11):
        lower = idx * 10
        upper = min(100, lower + 10)
        if v >= upper:
            segments.append(ATTACKER_EMOJI)
        elif v >= lower:
            segments.append(HIGHLIGHT_EMOJI)
        else:
            segments.append(BACKGROUND_EMOJI)
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
