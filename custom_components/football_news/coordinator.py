"""Coordinator: fast HA startup; bounded requests; staleness surfaced to UI."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, LEAGUES
from .provider import FootballProvider, ProviderError

_LOGGER = logging.getLogger(__name__)


class FootballNewsCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Each dataset has an independent refresh time and last-good fallback."""

    def __init__(self, hass, entry, provider: FootballProvider):
        super().__init__(
            hass, _LOGGER, name=f"Football News · {LEAGUES.get(provider.league, provider.league)}",
            update_interval=timedelta(seconds=300), config_entry=entry,
        )
        self.entry = entry
        self.provider = provider
        self.notifier = None
        self._dataset_updates: dict[str, datetime] = {}
        self._data: dict[str, Any] = {"fixtures": [], "standings": [], "news": []}
        self._notification_lock = asyncio.Lock()

    async def _async_update_data(self) -> dict[str, Any]:
        """Only poll scoreboard each cycle; expensive feeds obey separate TTLs."""
        tasks = {
            "fixtures": self.provider.fixtures(),
            "standings": self.provider.standings(),
            "news": self.provider.news(),
        }
        results = await asyncio.gather(*tasks.values(), return_exceptions=True)
        failures = []
        updated = []
        for name, result in zip(tasks, results, strict=True):
            if isinstance(result, Exception):
                failures.append(f"{name}: {type(result).__name__}: {result}")
            else:
                self._data[name] = result
                self._dataset_updates[name] = datetime.now(timezone.utc)
                updated.append(name)
        # Do not replace good data if the upstream request has a transient failure.
        if failures:
            _LOGGER.warning("Football News refresh partial failure: %s", "; ".join(failures))
        if failures and not self._dataset_updates:
            raise UpdateFailed("All upstream datasets are unavailable")
        active = any(item.get("state") == "in" for item in self._data["fixtures"])
        self.update_interval = timedelta(seconds=60 if active else 300)
        result = {**self._data, "league": LEAGUES.get(self.provider.league, self.provider.league),
                  "source": "ESPN (unofficial public endpoints)",
                  "updated_at": {key: timestamp.isoformat() for key, timestamp in self._dataset_updates.items()},
                  "errors": failures[:3]}
        _LOGGER.debug("Refresh %s: %d fixtures, %d standings rows, %d news items; updated %s; live=%s",
                      self.provider.league, len(result["fixtures"]), len(result["standings"]),
                      len(result["news"]), ",".join(updated), active)
        if self.notifier is not None:
            # Do not block entity updates or Home Assistant startup on Zalo I/O.
            self.hass.async_create_task(self.notifier.process(result))
        return result
