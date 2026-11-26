"""Pure scheduling decisions for ESPN soccer feeds.

The coordinator makes one decision per configured competition, independent of
how many dashboards are open. All timestamps are UTC and are supplied by ESPN.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class RefreshPlan:
    mode: str
    seconds: int
    days: tuple[str, ...] = ()


def _kickoff(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def refresh_plan(fixtures: list[dict], now: datetime | None = None,
                 live_seconds: int = 20) -> RefreshPlan:
    """Choose bounded polling and targeted scoreboard days.

    The fast path is used only for a live / imminent / recently finished match.
    Pre-match holds a fast watch after kickoff if ESPN hasn't switched to Live.
    Only relevant UTC dates are fetched, including a match spanning midnight.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    live_seconds = live_seconds if live_seconds in (15, 20, 30, 45, 60) else 20
    mode, interval = "idle", 300
    focus: set[str] = set()
    for match in fixtures:
        if not isinstance(match, dict):
            continue
        state = match.get("state")
        kickoff = _kickoff(match.get("kickoff"))
        minutes = (kickoff - now).total_seconds() / 60 if kickoff else None
        if state == "in" and (minutes is None or minutes >= -360):
            # A stuck upstream 'in' flag must not trigger rapid polling forever.
            mode, interval = "live", live_seconds
            # If ESPN omitted kickoff, search UTC today and yesterday. A game
            # crossing midnight can still be indexed under the prior day.
            if kickoff:
                focus.add(kickoff.strftime("%Y%m%d"))
            else:
                focus.update((now.strftime("%Y%m%d"),
                              (now - timedelta(days=1)).strftime("%Y%m%d")))
        elif state == "pre" and minutes is not None and -180 <= minutes <= 180:
            if minutes <= 10:
                candidate = ("kickoff", 30)
            elif minutes <= 60:
                candidate = ("warmup", 60)
            else:
                candidate = ("upcoming", 150)
            if mode != "live" and candidate[1] < interval:
                mode, interval = candidate
            if -180 <= minutes <= 65:
                focus.add(kickoff.strftime("%Y%m%d"))
        elif state == "post" and minutes is not None and -240 <= minutes <= 0:
            if mode not in ("live", "kickoff") and interval > 60:
                mode, interval = "settling", 60
            focus.add(kickoff.strftime("%Y%m%d"))
    # ESPN day queries can use a competition/local date, not UTC. For a match
    # at 00:00-05:59 UTC, also check the preceding day where ESPN may index it.
    for match in fixtures:
        if not isinstance(match, dict) or match.get("state") not in ("in", "pre", "post"):
            continue
        kickoff = _kickoff(match.get("kickoff"))
        if kickoff and kickoff.strftime("%Y%m%d") in focus and kickoff.hour < 6:
            focus.add((kickoff - timedelta(days=1)).strftime("%Y%m%d"))
    # At worst three match days per league per tick. Do not fan out over weeks.
    return RefreshPlan(mode, interval, tuple(sorted(focus)[:3]))


def merge_fixtures(calendar: list[dict], day_updates: list[dict]) -> list[dict]:
    """Daily scoreboard overrides older monthly rows by stable event ID."""
    merged = {str(item["id"]): item for item in calendar if isinstance(item, dict) and item.get("id")}
    for item in day_updates:
        if isinstance(item, dict) and item.get("id"):
            merged[str(item["id"])] = item
    return sorted(merged.values(), key=lambda item: item.get("kickoff") or "")[:400]
