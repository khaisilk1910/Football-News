"""Bounded, non-sensitive ESPN snapshot persistence via Home Assistant Store.

Only public football information is stored. The cache is per config entry to
prevent cross-league contamination. All file I/O is delegated to HA's Store.
"""
from __future__ import annotations

import re

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

from homeassistant.helpers.storage import Store

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Limits bound Recorder-independent disk use and prevent preserving old live
# status indefinitely. Data restored from disk is always marked as cached.
MAX_ROWS = {"fixtures": 400, "standings": 80, "news": 30, "leaders": 120}
MAX_AGE = {"fixtures": timedelta(days=7), "standings": timedelta(days=14),
           "news": timedelta(days=2), "leaders": timedelta(hours=24)}
MAX_SNAPSHOT_BYTES = 1_500_000


def parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result if result.tzinfo is not None else None
    except ValueError:
        return None


def safe_competition_logo(value: object) -> str:
    """Only persist official ESPN soccer competition logo URLs, not arbitrary URLs."""
    if isinstance(value, str) and re.fullmatch(
        r"https://a\.espncdn\.com/i/leaguelogos/soccer/500(?:-dark)?/[0-9]+\.png",
        value,
    ):
        return value
    return ""


def validated_snapshot(document: Any, league: str, now: datetime | None = None,
                       season: int | None = None) -> dict:
    """Return only recent, correctly scoped ESPN data; reject malformed JSON."""
    now = now or datetime.now(timezone.utc)
    if (not isinstance(document, dict) or document.get("league") != league or
            document.get("schema") != 1 or
            (season is not None and document.get("season") != season)):
        return {"datasets": {}, "updated_at": {}}
    values, stamps = {}, {}
    raw = document.get("datasets")
    updates = document.get("updated_at")
    if not isinstance(raw, dict) or not isinstance(updates, dict):
        return {"datasets": {}, "updated_at": {}}
    for name, limit in MAX_ROWS.items():
        stamp = parse_time(updates.get(name))
        rows = raw.get(name)
        if stamp is None or not isinstance(rows, list):
            continue
        age = now - stamp
        if age < timedelta(minutes=-5) or age > MAX_AGE[name]:
            continue
        if len(rows) > limit or any(not isinstance(row, dict) for row in rows):
            continue
        # A legitimate league table must include teams. Never treat a
        # previously stored empty ESPN stub as a freshly restored table.
        if name == "standings" and not rows:
            continue
        # Never claim a fixture is currently live on the basis of persisted
        # data; a fresh score request determines whether a match is live.
        if name == "fixtures":
            rows = [({**item, "state": "unknown", "status": "Cached — awaiting ESPN"}
                     if item.get("state") == "in" else item.copy()) for item in rows]
        values[name] = rows
        stamps[name] = stamp.isoformat()
    return {"datasets": values, "updated_at": stamps,
            "league_logo": safe_competition_logo(document.get("league_logo"))}


class FootballDiskCache:
    """HA-managed atomic disk store, never called from a worker thread."""

    def __init__(self, hass, entry_id: str, league: str, season: int) -> None:
        self.league = league
        self.season = season
        self.store = Store(hass, 1, f"{DOMAIN}_cache_{entry_id}")

    async def load(self) -> dict:
        try:
            document = await self.store.async_load()
        except (OSError, ValueError, TypeError) as err:
            _LOGGER.warning("Football News disk cache could not load league=%s error=%s",
                            self.league, type(err).__name__)
            return {"datasets": {}, "updated_at": {}}
        result = validated_snapshot(document, self.league, season=self.season)
        if document is not None and not result["datasets"]:
            _LOGGER.debug("Football News disk cache expired/invalid league=%s season=%s",
                          self.league, self.season)
        return result

    def schedule_save(self, data: dict[str, list[dict]], updates: dict[str, str],
                      league_logo: str = "") -> None:
        """Debounce writes and keep serialization on HA's disk storage path."""
        payload = {"schema": 1, "league": self.league, "season": self.season,
                   "league_logo": safe_competition_logo(league_logo),
                   "datasets": {name: ([{key: value for key, value in row.items() if key != "photo"}
                                        for row in rows[:MAX_ROWS[name]]] if name == "leaders"
                                       else rows[:MAX_ROWS[name]])
                                for name, rows in data.items()
                                if name in MAX_ROWS and isinstance(rows, list)},
                   "updated_at": {name: stamp for name, stamp in updates.items()
                                  if name in MAX_ROWS and isinstance(stamp, str)}}
        try:
            if len(json.dumps(payload, ensure_ascii=False, allow_nan=False)) > MAX_SNAPSHOT_BYTES:
                _LOGGER.warning("Football News disk snapshot too large, not saving league=%s", self.league)
                return
        except (TypeError, ValueError):
            _LOGGER.warning("Football News disk snapshot invalid, not saving league=%s", self.league)
            return
        self.store.async_delay_save(lambda: payload, 2.0)
