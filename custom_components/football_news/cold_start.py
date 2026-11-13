"""Cold-start ESPN cache bridge for WebSocket access before config entry setup.

Home Assistant creates a config entry before invoking its async_setup_entry.
A panel can open during that interval. Read only local Store data, once per
entry (with single-flight lock), and never wait on the ESPN network here.
"""
from __future__ import annotations

import asyncio
from time import monotonic

from .const import season_year_for_league
from .disk_cache import FootballDiskCache


class FootballColdStartCache:
    """Temporary in-memory index for read-only disk snapshots at startup."""

    def __init__(self, hass) -> None:
        self._hass = hass
        self._loaded: dict[tuple[str, str, int], tuple[float, dict]] = {}
        self._locks: dict[tuple[str, str, int], asyncio.Lock] = {}

    async def async_entry_snapshot(self, entry) -> dict:
        league = entry.data.get("league", "")
        if not league:
            return {}
        season = season_year_for_league(league)
        key = (entry.entry_id, league, season)
        result = self._loaded.get(key)
        # Recheck an empty snapshot quickly; periodically revalidate nonempty
        # entries to respect disk expiry and newly persisted ESPN results.
        if result is not None and monotonic() - result[0] < (60 if result[1] else 3):
            return result[1]
        lock = self._locks.setdefault(key, asyncio.Lock())
        async with lock:
            result = self._loaded.get(key)
            if result is not None and monotonic() - result[0] < (60 if result[1] else 3):
                return result[1]
            stored = await FootballDiskCache(self._hass, entry.entry_id, league, season).load()
            datasets = stored.get("datasets", {})
            snapshot = ({
                "fixtures": datasets.get("fixtures", []),
                "standings": datasets.get("standings", []),
                "news": datasets.get("news", []),
                "updated_at": stored.get("updated_at", {}),
                "league_logo": stored.get("league_logo", ""),
                "cache_info": {"type": "disk", "restored_datasets": sorted(datasets)},
                "errors": [],
            } if datasets else {})
            self._loaded[key] = (monotonic(), snapshot)
            return snapshot
