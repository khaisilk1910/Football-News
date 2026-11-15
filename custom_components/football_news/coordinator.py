"""Coordinators with bounded RAM and durable HA Store ESPN snapshots.

Cold startup never waits for ESPN. The first panel request can await *local*
storage while background refresh later replaces each dataset independently.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import LEAGUES
from .disk_cache import FootballDiskCache, parse_time
from .provider import FootballProvider, ProviderError

_LOGGER = logging.getLogger(__name__)
_DATASETS = ("fixtures", "standings", "news")


class FootballNewsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Refresh ESPN asynchronously and restore the last known public data."""

    def __init__(self, hass, entry, provider: FootballProvider):
        super().__init__(
            hass, _LOGGER, name=f"Football News · {LEAGUES.get(provider.league, provider.league)}",
            update_interval=timedelta(seconds=300), config_entry=entry,
        )
        self.entry = entry
        self.provider = provider
        self.notifier = None
        self._dataset_updates: dict[str, datetime] = {}
        self._data: dict[str, Any] = {key: [] for key in _DATASETS}
        self._leader_rows: list[dict] = []
        self._leader_updated: datetime | None = None
        self._leader_lock = asyncio.Lock()
        self._notification_lock = asyncio.Lock()
        self._last_errors: list[str] = []
        self._error_log_signature: tuple[str, ...] = ()
        self._last_error_logged = 0.0
        self._attempted_refresh = False
        self._disk = FootballDiskCache(hass, entry.entry_id, provider.league, provider._season_year())
        self._restore_lock = asyncio.Lock()
        self._cache_loaded = False
        self._restored_datasets: set[str] = set()
        self._empty_streak: dict[str, int] = {key: 0 for key in _DATASETS}

    def _snapshot(self, errors: list[str] | None = None) -> dict[str, Any]:
        return {
            **self._data,
            "league": LEAGUES.get(self.provider.league, self.provider.league),
            "league_logo": getattr(self.provider, "league_logo", ""),
            "source": "ESPN (unofficial public endpoints)",
            "updated_at": {key: stamp.isoformat() for key, stamp in self._dataset_updates.items()},
            "errors": errors if errors is not None else self._last_errors[:3],
            "cache_info": {"restored_datasets": sorted(self._restored_datasets),
                           "type": "disk" if self._restored_datasets else "memory"},
        }

    async def async_restore_cache(self) -> None:
        """Restore only once, with a lock shared by startup and panel requests."""
        if self._cache_loaded:
            return
        async with self._restore_lock:
            if self._cache_loaded:
                return
            try:
                cached = await self._disk.load()
                if cached.get("league_logo") and not getattr(self.provider, "league_logo", ""):
                    self.provider.league_logo = cached["league_logo"]
                for name, rows in cached["datasets"].items():
                    timestamp = parse_time(cached["updated_at"].get(name))
                    if timestamp is None:
                        continue
                    if name == "leaders":
                        if self._leader_updated is None or self._leader_updated < timestamp:
                            self._leader_rows = rows
                            self._leader_updated = timestamp
                            self._restored_datasets.add("leaders")
                        continue
                    # Never overwrite fresh RAM data with a slower disk read.
                    if name in _DATASETS and (name not in self._dataset_updates or
                                               self._dataset_updates[name] < timestamp):
                        self._data[name] = rows
                        self._dataset_updates[name] = timestamp
                        self._restored_datasets.add(name)
                if self._restored_datasets:
                    self.async_set_updated_data(self._snapshot())
                    _LOGGER.info("Football News restored disk cache league=%s datasets=%s",
                                 self.provider.league, ",".join(sorted(self._restored_datasets)))
            except Exception:
                # Cache corruption/IO must not prevent ESPN or HA setup.
                _LOGGER.exception("Football News cache restore failed league=%s", self.provider.league)
            finally:
                self._cache_loaded = True

    def _persist(self, force: bool = False) -> None:
        """Debounce safely through Store; never skip a newly successful feed.

        A coarse 120-second global throttle used to drop a standings update
        when fixtures finished earlier in the same refresh window. HA Store
        already deduplicates pending async_delay_save writes to the same key.
        """
        feeds = {name: self._data[name] for name in _DATASETS if name in self._dataset_updates}
        updates = {name: stamp.isoformat() for name, stamp in self._dataset_updates.items()}
        if self._leader_updated is not None and self._leader_rows:
            feeds["leaders"] = self._leader_rows
            updates["leaders"] = self._leader_updated.isoformat()
        if not feeds:
            return
        self._disk.schedule_save(feeds, updates, getattr(self.provider, "league_logo", ""))

    async def async_leaders(self) -> tuple[list[dict], bool]:
        """Use RAM/disk for recent leaders and refresh ESPN only on demand."""
        await self.async_restore_cache()
        async with self._leader_lock:
            if (self._leader_rows and self._leader_updated and
                    datetime.now(timezone.utc) - self._leader_updated < timedelta(hours=6)):
                return self._leader_rows, bool("leaders" in self._restored_datasets)
            try:
                rows = await self.provider.leaders()
            except ProviderError:
                if self._leader_rows and self._leader_updated:
                    _LOGGER.warning("ESPN player leaders unavailable; using prior data league=%s",
                                    self.provider.league)
                    return self._leader_rows, True
                raise
            if not rows and self._leader_rows:
                _LOGGER.debug("ESPN leaders empty league=%s; retaining prior leaderboard", self.provider.league)
                return self._leader_rows, True
            if rows:
                self._leader_rows = rows[:120]
                self._leader_updated = datetime.now(timezone.utc)
                self._restored_datasets.discard("leaders")
                self._persist(force=True)
            return rows, False

    async def _async_update_data(self) -> dict[str, Any]:
        """ESPN refresh runs after startup; last-good datasets survive errors."""
        await self.async_restore_cache()
        tasks = {
            "fixtures": self.provider.fixtures(),
            "standings": self.provider.standings(),
            "news": self.provider.news(),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        failures, updated = [], []
        for name, result in zip(tasks, results, strict=True):
            if isinstance(result, Exception):
                self._empty_streak[name] = 0
                failures.append(f"{name}: {type(result).__name__}: {result}")
            else:
                # A standings table with zero rows is not a valid updated
                # snapshot. Always keep the last successful table until ESPN
                # supplies new entries; knockout tournaments are the exception.
                if name == "standings" and not result:
                    if self._data[name]:
                        failures.append("standings: ESPN returned no teams; retaining last-good table")
                    continue
                # ESPN occasionally returns a successful but empty response
                # while other feeds still work. Require one confirmation
                # before replacing a non-empty last-good dataset with [].
                if isinstance(result, list) and not result and self._data[name]:
                    self._empty_streak[name] += 1
                    if self._empty_streak[name] < 2:
                        failures.append(f"{name}: empty ESPN response; retaining last-good data until confirmed")
                        continue
                self._empty_streak[name] = 0
                self._data[name] = result
                self._dataset_updates[name] = datetime.now(timezone.utc)
                self._restored_datasets.discard(name)
                updated.append(name)
        self._attempted_refresh = True
        self._last_errors = failures[:3]
        if failures:
            # Keep details in diagnostics but avoid flooding Home Assistant
            # logs on every scheduled refresh during a prolonged ESPN outage.
            signature = tuple(failures)
            now = monotonic()
            if signature != self._error_log_signature or now - self._last_error_logged >= 1800:
                _LOGGER.warning("Football News refresh partial failure league=%s: %s",
                                self.provider.league, "; ".join(failures))
                self._last_error_logged = now
                self._error_log_signature = signature
            else:
                _LOGGER.debug("Football News ESPN still unavailable league=%s", self.provider.league)
        elif self._error_log_signature:
            _LOGGER.info("Football News ESPN feeds recovered league=%s", self.provider.league)
            self._error_log_signature = ()
        if failures and not self._dataset_updates:
            raise UpdateFailed("All upstream datasets are unavailable")
        active = any(item.get("state") == "in" for item in self._data["fixtures"])
        self.update_interval = timedelta(seconds=60 if active else 300)
        result = self._snapshot(failures[:3])
        if updated:
            self._persist()
        _LOGGER.debug("Refresh %s: %d fixtures, %d standings, %d news; updated=%s; disk=%s live=%s",
                      self.provider.league, len(result["fixtures"]), len(result["standings"]),
                      len(result["news"]), ",".join(updated),
                      ",".join(sorted(self._restored_datasets)), active)
        if self.notifier is not None and ("fixtures" in updated or "news" in updated):
            # Keep the notification pipeline working through partial ESPN
            # outages, but never dispatch old fixtures/news loaded from disk.
            notifications = {**result,
                             "fixtures": result["fixtures"] if "fixtures" in updated else [],
                             "news": result["news"] if "news" in updated else []}
            self.hass.async_create_task(self.notifier.process(notifications))
        return result
