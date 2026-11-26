"""Durable, server-only index for cold-start reads of configured competitions.

A Home Assistant config-entry registry may be temporarily unavailable to a
custom panel during reload. The last *known configured* entry IDs allow us to
read their HA Store football snapshots without ESPN or browser-local data.
Entries are removed from this index when HA removes the config entry, not when
an integration is unloaded/restarted.
"""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from types import SimpleNamespace
from time import monotonic

from homeassistant.helpers.storage import Store

from .const import DOMAIN, LEAGUES

_LOGGER = logging.getLogger(__name__)
_MAX_ENTRIES = 32


class FootballLeagueRegistry:
    """Index only entry IDs and league codes; no tokens or football payloads."""

    def __init__(self, hass) -> None:
        self._store = Store(hass, 1, f"{DOMAIN}_league_registry")
        self._rows: dict[str, str] = {}
        self._loaded = False
        self._lock = asyncio.Lock()
        self._last_fallback_notice_at = 0.0
        self._last_fallback_counts: tuple[int, int] | None = None

    async def _load(self) -> None:
        if self._loaded:
            return
        try:
            value = await self._store.async_load()
        except Exception:
            _LOGGER.exception("Football News league registry could not be read; current HA entries remain authoritative")
            value = None
        items = value.get("entries", {}) if isinstance(value, dict) else {}
        if isinstance(items, dict):
            self._rows = {key: code for key, code in list(items.items())[:_MAX_ENTRIES]
                          if isinstance(key, str) and re.fullmatch(r"[a-zA-Z0-9_-]{1,128}", key)
                          and isinstance(code, str) and code in LEAGUES}
        self._loaded = True

    def _save(self) -> None:
        self._store.async_delay_save(lambda: {
            "entries": dict(self._rows),
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }, 1.0)

    def note_fallback(self, missing: int, native: int) -> None:
        """Log restoration once per state transition, then at most each minute."""
        counts = (missing, native)
        now = monotonic()
        if counts != self._last_fallback_counts or now - self._last_fallback_notice_at >= 60:
            self._last_fallback_counts = counts
            self._last_fallback_notice_at = now
            _LOGGER.warning(
                "Football News config-entry registry incomplete; serving %d HA-saved league(s) "
                "while %d native entry(s) are ready", missing, native)

    async def remember(self, entries) -> None:
        """Record entries without blocking HA startup or accessing ESPN."""
        async with self._lock:
            await self._load()
            added = 0
            for entry in entries:
                code = entry.data.get("league", "")
                if code in LEAGUES and self._rows.get(entry.entry_id) != code:
                    self._rows[entry.entry_id] = code
                    added += 1
            if added:
                self._save()
                _LOGGER.info("Football News durable league registry recorded %d entry(s), total=%d",
                             added, len(self._rows))

    async def forget(self, entry_id: str) -> None:
        async with self._lock:
            await self._load()
            if self._rows.pop(entry_id, None) is not None:
                self._save()
                _LOGGER.info("Football News durable league registry removed entry=%s", entry_id)

    async def fallback_entries(self) -> list:
        """Return read-only stand-ins when HA's registry is temporarily empty."""
        async with self._lock:
            await self._load()
            return [SimpleNamespace(entry_id=entry_id, data={"league": code},
                                    options={}, runtime_data=None,
                                    state="registry_restoring")
                    for entry_id, code in self._rows.items()]
