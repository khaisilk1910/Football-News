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
from .adaptive import RefreshPlan, merge_fixtures, refresh_plan
from .disk_cache import FootballDiskCache, parse_time
from .live_events import LiveEventTracker, fixture_score_from_summary
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
        self._history_rows: list[dict] = []
        self._history_updated: datetime | None = None
        self._history_lock = asyncio.Lock()
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
        self._calendar_checked_at: float | None = None
        self._last_persisted_at = 0.0
        self._last_visible_change = True
        self._poll_plan = RefreshPlan("idle", 300)
        self._live_event_tracker = LiveEventTracker()
        self._live_event_task: asyncio.Task | None = None
        self._live_event_cursor = 0
        self._live_events_stopped = False

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
            "refresh_policy": {"mode": self._poll_plan.mode,
                               "seconds": self._poll_plan.seconds,
                               "focused_days": list(self._poll_plan.days)},
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
                    if name == "history":
                        if self._history_updated is None or self._history_updated < timestamp:
                            self._history_rows = rows
                            self._history_updated = timestamp
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
            except asyncio.CancelledError:
                # A timed-out first-view WebSocket must not mark an unfinished
                # HA Store read as a successfully hydrated, empty cache.
                _LOGGER.debug('Football News cache hydration cancelled; retry permitted league=%s',
                              self.provider.league)
                raise
            else:
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
        if self._history_updated is not None and self._history_rows:
            feeds["history"] = self._history_rows
            updates["history"] = self._history_updated.isoformat()
        if not feeds:
            return
        self._disk.schedule_save(feeds, updates, getattr(self.provider, "league_logo", ""))

    async def async_favourite_form(self, team_ids: list[str]) -> dict:
        """Serve recent results from HA Store, supplementing only on demand.

        HA restart and browser reload never discard the 10-match history that
        was previously fetched. One coordinator lock serializes concurrent
        desktop/mobile requests, and the provider shares monthly ESPN cache.
        """
        await self.async_restore_cache()
        async with self._history_lock:
            known = list(self._history_rows) + list(self._data.get("fixtures", []))
            result = await self.provider.favourite_form_history(team_ids, known)
            if result.get("fixtures"):
                merged = {str(item["id"]): item for item in self._history_rows
                          if isinstance(item, dict) and item.get("id")}
                for item in result["fixtures"]:
                    merged[str(item["id"])] = item
                # The history belongs to this league/config entry only, and
                # is bounded independently of the regular 14-day calendar.
                rows = sorted(merged.values(), key=lambda item: item.get("kickoff") or "",
                              reverse=True)[:100]
                if rows != self._history_rows:
                    self._history_rows = rows
                    self._history_updated = datetime.now(timezone.utc)
                    self._persist(force=True)
            return result

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
                # Leaderboard is also server-owned. Notify other open panels
                # when an on-demand refresh replaces the shared dataset.
                self.hass.bus.async_fire("football_news_leaders_updated",
                                         {"league": self.provider.league})
            return rows, False

    def _log_score_changes(self, previous: list[dict], fresh: list[dict]) -> None:
        """Useful, low-volume logs for real ESPN score/status transitions."""
        before = {str(item.get("id")): item for item in previous if isinstance(item, dict)}
        for item in fresh:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            prior = before.get(str(item["id"]))
            if not prior:
                continue
            old_score = (prior.get("home", {}).get("score"), prior.get("away", {}).get("score"))
            new_score = (item.get("home", {}).get("score"), item.get("away", {}).get("score"))
            old_state, new_state = prior.get("state"), item.get("state")
            if old_score != new_score or old_state != new_state:
                _LOGGER.info("Football News match changed league=%s event=%s status=%s->%s score=%s->%s",
                             self.provider.league, item["id"], old_state, new_state,
                             old_score, new_score)

    def _choose_plan(self, fixtures: list[dict]) -> RefreshPlan:
        speed = getattr(self.entry, "options", {}).get("live_refresh_seconds", 20)
        return refresh_plan(fixtures, live_seconds=speed)

    async def _refresh_fixtures(self, plan: RefreshPlan) -> list[dict]:
        """Fetch short-lived matchday scores and slow calendar independently.

        Active games must never wait for the two-minute month cache to expire.
        During Live, use only today's relevant matchday(s) on most ticks;
        periodically reconcile the full 14/35-day fixture calendar.
        """
        now = monotonic()
        calendar_due = (self._calendar_checked_at is None or
                        now - self._calendar_checked_at >= 300 or
                        not self._dataset_updates.get("fixtures"))
        if not plan.days:
            rows = await self.provider.fixtures()
            self._calendar_checked_at = monotonic()
            return rows

        if not calendar_due:
            fresh = await self.provider.live_fixtures(plan.days)
            return merge_fixtures(self._data["fixtures"], fresh)

        calendar, daily = await asyncio.gather(
            self.provider.fixtures(), self.provider.live_fixtures(plan.days),
            return_exceptions=True,
        )
        if not isinstance(calendar, Exception):
            self._calendar_checked_at = monotonic()
        if isinstance(calendar, Exception) and isinstance(daily, Exception):
            raise ProviderError("Calendar and live scoreboard unavailable: " +
                                f"{type(calendar).__name__}, {type(daily).__name__}")
        if isinstance(calendar, Exception):
            _LOGGER.debug("Calendar unavailable league=%s; merging fresh matchday scores",
                          self.provider.league)
            return merge_fixtures(self._data["fixtures"], daily)
        if isinstance(daily, Exception):
            _LOGGER.debug("Live scoreboard unavailable league=%s; using calendar snapshot",
                          self.provider.league)
            # A stale calendar may still mark an already completed match as
            # Live. Preserve its confirmed final status from the last daily
            # response, but accept a newer calendar's own final result.
            by_id = {str(item.get("id")): item for item in calendar}
            stable = [item for item in self._data["fixtures"]
                      if item.get("state") in ("in", "post") and
                      by_id.get(str(item.get("id")), {}).get("state") != "post"]
            return merge_fixtures(calendar, stable)
        return merge_fixtures(calendar, daily)

    async def _poll_live_events(self, fixtures: list[dict]) -> None:
        """Fetch ESPN keyEvents after refresh, never blocking the coordinator.

        A bounded rotation avoids burst requests when a competition has many
        simultaneous games. All panels receive the same HA bus events; no
        device opens a second ESPN event poll.
        """
        candidates = [item for item in fixtures if isinstance(item, dict)
                      and item.get("state") == "in" and str(item.get("id", "")).isdigit()]
        if not candidates or self._live_events_stopped:
            return
        cap = min(len(candidates), 8)
        start = self._live_event_cursor % len(candidates)
        selection = (candidates + candidates)[start:start + cap]
        self._live_event_cursor = (start + cap) % len(candidates)
        limit = asyncio.Semaphore(2)

        async def inspect(fixture: dict) -> None:
            async with limit:
                if self._live_events_stopped:
                    return
                try:
                    summary = await self.provider.summary(str(fixture["id"]))
                    fresh_fixture = fixture_score_from_summary(fixture, summary)
                    for event in self._live_event_tracker.update(fresh_fixture, summary):
                        if self._live_events_stopped:
                            return
                        self.hass.bus.async_fire("football_news_live_event", event)
                        _LOGGER.info("Football News Live event league=%s match=%s type=%s minute=%s",
                                     self.provider.league, fixture["id"], event["type"],
                                     event["minute"] or "unknown")
                except Exception as err:
                    # Provider cooldown handles 429s and transient connection
                    # errors. Never lose the last-good scoreboard on a timeline
                    # failure, or create a busy retry loop.
                    _LOGGER.debug("Football News Live timeline unavailable league=%s match=%s error=%s",
                                  self.provider.league, fixture["id"], type(err).__name__)

        await asyncio.gather(*(inspect(item) for item in selection))

    def _schedule_live_events(self, fixtures: list[dict]) -> None:
        if (self._live_events_stopped or self._poll_plan.mode != "live" or
                not callable(getattr(self.provider, "summary", None)) or
                not any(item.get("state") == "in" for item in fixtures)):
            return
        if self._live_event_task and not self._live_event_task.done():
            return
        self._live_event_task = self.hass.async_create_task(self._poll_live_events(fixtures))

    async def async_stop_live_events(self) -> None:
        """Do not fire events from a coordinator after its entry unloads."""
        self._live_events_stopped = True
        task = self._live_event_task
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    async def _async_update_data(self) -> dict[str, Any]:
        """ESPN refresh runs after startup; last-good datasets survive errors."""
        await self.async_restore_cache()
        old_plan = self._poll_plan
        self._poll_plan = self._choose_plan(self._data["fixtures"])
        tasks = {
            "fixtures": self._refresh_fixtures(self._poll_plan),
            "standings": self.provider.standings(),
            "news": self.provider.news(),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        failures, updated, changed = [], [], []
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
                if result != self._data[name]:
                    changed.append(name)
                    if name == "fixtures":
                        self._log_score_changes(self._data[name], result)
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
        self._poll_plan = self._choose_plan(self._data["fixtures"])
        self.update_interval = timedelta(seconds=self._poll_plan.seconds)
        self._last_visible_change = bool(changed)
        if "fixtures" in updated:
            self._schedule_live_events(self._data["fixtures"])
        result = self._snapshot(failures[:3])
        # Live score may be checked every 15-20s. Avoid a disk write and a
        # duplicate goal notification every time ESPN returns identical data.
        if updated and (changed or monotonic() - self._last_persisted_at >= 300):
            self._persist()
            self._last_persisted_at = monotonic()
        if old_plan.mode != self._poll_plan.mode:
            _LOGGER.info("Football News polling league=%s mode=%s -> %s interval=%ss days=%s",
                         self.provider.league, old_plan.mode, self._poll_plan.mode,
                         self._poll_plan.seconds, ",".join(self._poll_plan.days) or "none")
        _LOGGER.debug("Refresh %s: %d fixtures, %d standings, %d news; updated=%s changed=%s; cache=%s polling=%s/%ss",
                      self.provider.league, len(result["fixtures"]), len(result["standings"]),
                      len(result["news"]), ",".join(updated), ",".join(changed),
                      ",".join(sorted(self._restored_datasets)),
                      self._poll_plan.mode, self._poll_plan.seconds)
        if self.notifier is not None and ("fixtures" in changed or "news" in changed):
            # Keep the notification pipeline working through partial ESPN
            # outages, but never dispatch old fixtures/news loaded from disk.
            notifications = {**result,
                             "fixtures": result["fixtures"] if "fixtures" in changed else [],
                             "news": result["news"] if "news" in changed else []}
            self.hass.async_create_task(self.notifier.process(notifications))
        return result
