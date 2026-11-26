"""Verified ESPN Live match events for in-panel Home Assistant alerts.

This module has no I/O and no HA imports. Events are baselined on the first
valid ESPN timeline per match so opening a view never replays historical goals.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from time import monotonic
from typing import Any

from .const import LEAGUES


def _obj(value: Any) -> dict:
    return value if isinstance(value, dict) else {}


def _str(value: Any, maximum: int = 150) -> str:
    return str(value).strip()[:maximum] if value is not None else ""


def event_kind(event: dict) -> str:
    """Only announce clearly classified goals or yellow/red cards.

    ESPN may report VAR reviews, missed penalties and disallowed goals in the
    same keyEvents list; none of those should be announced as scored goals.
    """
    kind = _obj(event.get("type"))
    label = _str(kind.get("text") or kind.get("name") or kind.get("displayName")
                 or event.get("typeText")).casefold()
    desc = _str(event.get("text") or event.get("description") or event.get("shortText"), 400).casefold()
    combined = f"{label} {desc}"
    if any(word in combined for word in ("disallowed", "overturned", "no goal", "goal cancelled",
                                          "goal canceled", "missed penalty", "penalty missed")):
        return ""
    if ("red card" in label or "second yellow" in combined or "2nd yellow" in combined or
            "yellow/red" in combined or (label in {"card", "booking"} and "red card" in desc)):
        return "red"
    if "yellow card" in label or "booking" in label or (label == "card" and "yellow card" in desc):
        return "yellow"
    if ("goal" in label and "goal kick" not in label and "goalkeeper" not in label) or event.get("scoringPlay") is True:
        return "goal"
    if not label:
        if "red card" in desc or "second yellow" in desc or "2nd yellow" in desc:
            return "red"
        if "yellow card" in desc:
            return "yellow"
        if re.search(r"\bgoal[!: ]", desc) and "goal kick" not in desc:
            return "goal"
    return ""


def _goal_description(event: dict) -> str:
    """Extract source commentary, preferring full ESPN text over a short label."""
    texts = [" ".join(value.split()) for key in ("text", "description", "shortText")
             if isinstance((value := event.get(key)), str) and value.strip()]
    return max(texts, key=len)[:900] if texts else ""


def _player(event: dict) -> str:
    candidates = []
    for key in ("participants", "athletes"):
        if isinstance(event.get(key), list):
            candidates.extend(event[key][:5])
    candidates += [event.get("athlete"), event.get("player"), event.get("scorer")]
    for item in candidates:
        item = _obj(item)
        athlete = _obj(item.get("athlete")) or _obj(item.get("player")) or item
        name = _str(athlete.get("displayName") or athlete.get("fullName") or athlete.get("name"))
        if name:
            return name
    # ESPN's prose sometimes identifies a scorer even without participants.
    text = _str(event.get("text") or event.get("description"), 400)
    match = re.search(r"\b(?:Goal|Scored) by ([^.!\n()]{3,75})", text, re.IGNORECASE)
    return _str(match.group(1)) if match else ""


def fixture_score_from_summary(fixture: dict, summary: dict) -> dict:
    """Prefer the score published alongside the Live event when available.

    ESPN's daily scoreboard and detailed summary have independent cache ages.
    If a goal arrives in the timeline before the daily feed catches up, the
    event popup should use the fresh summary score, never guess a result.
    """
    header = _obj(_obj(summary).get("header"))
    competitions = header.get("competitions")
    if not isinstance(competitions, list) or not competitions:
        return fixture
    competitors = _obj(competitions[0]).get("competitors")
    if not isinstance(competitors, list):
        return fixture
    scores = {}
    for raw in competitors:
        row = _obj(raw)
        side = row.get("homeAway")
        if side not in ("home", "away"):
            continue
        value = row.get("score")
        if isinstance(value, dict):
            value = value.get("value", value.get("displayValue"))
        if type(value) is int:
            number = value
        elif isinstance(value, str) and value.isascii() and value.isdigit():
            number = int(value)
        else:
            continue
        if 0 <= number <= 99:
            scores[side] = number
    if len(scores) != 2:
        return fixture
    old_home = _obj(fixture.get("home")).get("score")
    old_away = _obj(fixture.get("away")).get("score")
    if (type(old_home) is int and type(old_away) is int and
            old_home + old_away > scores["home"] + scores["away"]):
        # A lower-score summary may be older than the daily scoreboard.
        return fixture
    return {**fixture, "home": {**_obj(fixture.get("home")), "score": scores["home"]},
            "away": {**_obj(fixture.get("away")), "score": scores["away"]}}


def extract_events(summary: dict, fixture: dict) -> list[dict] | None:
    """Return known event snapshots, or None when ESPN supplied no timeline.

    A timeline that exists but is empty is a valid baseline; an absent timeline
    is not evidence that the previous events disappeared.
    """
    if not isinstance(summary, dict):
        return None
    timeline = summary.get("keyEvents")
    if not isinstance(timeline, list):
        timeline = summary.get("scoringPlays")
    if not isinstance(timeline, list):
        return None
    match_id = _str(fixture.get("id"), 32)
    if not match_id or fixture.get("state") != "in":
        return []
    home, away = _obj(fixture.get("home")), _obj(fixture.get("away"))
    by_team = {_str(item.get("id")): item for item in (home, away) if item.get("id")}
    found, keys = [], set()
    for raw in timeline[:150]:
        event = _obj(raw)
        category = event_kind(event)
        if not category:
            continue
        clock = _obj(event.get("clock"))
        minute = _str(clock.get("displayValue") or event.get("displayClock") or
                      event.get("minute") or "", 18)
        team = _obj(event.get("team"))
        team_id = _str(team.get("id"), 32)
        club = by_team.get(team_id, {})
        if not club:
            name = _str(team.get("displayName") or team.get("name")).casefold()
            club = next((item for item in (home, away)
                         if _str(item.get("name")).casefold() == name and name), {})
        player = _player(event)
        raw_id = _str(event.get("id"), 100)
        # Prefer ESPN IDs. If unavailable, use stable match minute/team/player
        # instead of description, which ESPN can revise after VAR review.
        identity = (f"id:{raw_id}" if raw_id else
                    "fallback:" + "|".join((category, minute, team_id or _str(club.get("name")), player)))
        key = f"{match_id}:{identity}"
        if key in keys:
            continue
        keys.add(key)
        commentary = _goal_description(event) if category == "goal" else ""
        found.append({
            **({"description": commentary} if commentary else {}),
            "event_key": key,
            "type": category,
            "event_id": match_id,
            "league": _str(fixture.get("league")),
            "league_name": LEAGUES.get(_str(fixture.get("league")), _str(fixture.get("league"))),
            "minute": minute,
            "player": player,
            "team": _str(club.get("name") or team.get("displayName")),
            "home": {"name": _str(home.get("name")), "logo": _str(home.get("logo"), 350),
                     "score": home.get("score")},
            "away": {"name": _str(away.get("name")), "logo": _str(away.get("logo"), 350),
                     "score": away.get("score")},
        })
    return found


class LiveEventTracker:
    """Server-side deduplication for one Home Assistant league coordinator."""

    def __init__(self):
        self._seen: dict[str, set[str]] = {}
        self._touched: dict[str, float] = {}

    def update(self, fixture: dict, summary: dict) -> list[dict]:
        rows = extract_events(summary, fixture)
        if rows is None:
            return []
        match_id = _str(fixture.get("id"), 32)
        if not match_id or fixture.get("state") != "in":
            return []
        now = monotonic()
        for ident in list(self._touched):
            if now - self._touched[ident] > 8 * 3600:
                self._touched.pop(ident, None)
                self._seen.pop(ident, None)
        seen = self._seen.get(match_id)
        keys = {item["event_key"] for item in rows}
        self._touched[match_id] = now
        if seen is None:
            self._seen[match_id] = keys
            return []  # First good timeline is a baseline, not a new event.
        fresh = [item for item in rows if item["event_key"] not in seen]
        seen.update(keys)  # Keep all seen keys even if ESPN briefly omits one.
        stamp = datetime.now(timezone.utc).isoformat()
        for item in fresh:
            item["published_at"] = stamp
        return fresh
