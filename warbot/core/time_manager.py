"""Helpers for managing RP time tracking and reminders."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

DATA_ROOT = Path(
    os.getenv(
        "WAR_DATA_DIR",
        Path(__file__).resolve().parent.parent / "data",
    )
)
TIME_FILE = DATA_ROOT / "time.json"

DEFAULT_STATE: Dict[str, Any] = {
    "year": 2238,
    "season": 1,
    "season_names": ["Spring", "Summer", "Autumn", "Winter"],
    "next_timer_id": 1,
    "timers": [],
    "updated_at": None,
    "last_auto_date": None,
}


def _ensure_state_file() -> None:
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    if not TIME_FILE.exists():
        TIME_FILE.write_text(json.dumps(DEFAULT_STATE, indent=2), encoding="utf-8")


def load_time_state() -> Dict[str, Any]:
    """Return the persisted time state, creating defaults if missing."""
    _ensure_state_file()
    try:
        payload = json.loads(TIME_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        payload = DEFAULT_STATE.copy()

    payload.setdefault("year", DEFAULT_STATE["year"])
    payload.setdefault("season", DEFAULT_STATE["season"])
    payload.setdefault("season_names", DEFAULT_STATE["season_names"])
    payload.setdefault("next_timer_id", DEFAULT_STATE["next_timer_id"])
    payload.setdefault("timers", [])
    payload.setdefault("updated_at", None)
    payload.setdefault("last_auto_date", None)

    _normalize_season(payload)
    return payload


def save_time_state(state: Dict[str, Any]) -> None:
    """Persist the time state."""
    _ensure_state_file()
    with TIME_FILE.open("w", encoding="utf-8") as fp:
        json.dump(state, fp, indent=2, ensure_ascii=False)


def _normalize_season(state: Dict[str, Any]) -> None:
    seasons = state.get("season_names", DEFAULT_STATE["season_names"])
    if not isinstance(seasons, list) or len(seasons) != 4:
        seasons = DEFAULT_STATE["season_names"]
        state["season_names"] = seasons

    season = int(state.get("season", 1))
    if season < 1:
        season = 1
    elif season > 4:
        season = ((season - 1) % 4) + 1
    state["season"] = season


def format_time(state: Dict[str, Any]) -> str:
    """Return a formatted RP time string."""
    season_idx = int(state.get("season", 1)) - 1
    season_names = state.get("season_names", DEFAULT_STATE["season_names"])
    season_name = season_names[season_idx] if 0 <= season_idx < len(season_names) else "Season"
    return f"{int(state.get('year', 0))} {state['season']}/4 — {season_name}"


def current_turn_index(state: Dict[str, Any]) -> int:
    """Compute a monotonically increasing turn index."""
    year = int(state.get("year", DEFAULT_STATE["year"]))
    season = int(state.get("season", DEFAULT_STATE["season"]))
    return year * 4 + (season - 1)


def advance_turns(state: Dict[str, Any], turns: int) -> Dict[str, Any]:
    """Advance the state forward by ``turns`` seasons."""
    if turns <= 0:
        return state

    year = int(state.get("year", DEFAULT_STATE["year"]))
    season = int(state.get("season", DEFAULT_STATE["season"])) - 1
    season += turns
    delta_years, season = divmod(season, 4)
    year += delta_years

    state["year"] = year
    state["season"] = season + 1
    state["updated_at"] = _timestamp()
    return state


def set_time(state: Dict[str, Any], year: int, season: int) -> Dict[str, Any]:
    """Set the time state directly."""
    state["year"] = max(0, year)
    state["season"] = max(1, min(season, 4))
    state["updated_at"] = _timestamp()
    _normalize_season(state)
    return state


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def add_timer(
    state: Dict[str, Any],
    turns_from_now: int,
    description: str,
    channel_id: int,
    created_by: int,
) -> Dict[str, Any]:
    """Schedule a new timer relative to the current turn."""
    if turns_from_now <= 0:
        raise ValueError("Timer must be set at least one turn in the future.")

    trigger_turn = current_turn_index(state) + turns_from_now
    timer = {
        "id": state["next_timer_id"],
        "description": description,
        "turns": turns_from_now,
        "trigger_turn": trigger_turn,
        "channel_id": channel_id,
        "created_by": created_by,
        "created_at": _timestamp(),
    }
    state["next_timer_id"] += 1
    state.setdefault("timers", []).append(timer)
    return timer


def cancel_timer(state: Dict[str, Any], timer_id: int) -> bool:
    """Remove a timer by ID. Returns True if removed."""
    timers = state.get("timers", [])
    remaining = [timer for timer in timers if int(timer.get("id")) != int(timer_id)]
    if len(remaining) == len(timers):
        return False
    state["timers"] = remaining
    return True


def list_timers(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return timers sorted by trigger turn."""
    return sorted(state.get("timers", []), key=lambda item: item.get("trigger_turn", 0))


def collect_due_timers(state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Pop timers whose trigger turn is now or in the past."""
    current_turn = current_turn_index(state)
    timers = state.get("timers", [])
    due: List[Dict[str, Any]] = []
    remaining: List[Dict[str, Any]] = []

    for timer in timers:
        if int(timer.get("trigger_turn", current_turn + 1)) <= current_turn:
            due.append(timer)
        else:
            remaining.append(timer)

    if due:
        state["timers"] = remaining
    return sorted(due, key=lambda item: item.get("trigger_turn", 0))
