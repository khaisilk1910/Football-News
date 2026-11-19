"""Per-HA-account dashboard settings, shared by all that account's devices.

Football content and favourites are *global* HA-side stores; only personal
navigation/appearance is scoped to an authenticated HA user. Never use
browser-local persistence as another competing source of truth.

This store is loaded on the first frontend WebSocket read, not during startup.
"""
from __future__ import annotations

import asyncio
import logging

from homeassistant.helpers.storage import Store

from .const import DOMAIN, LEAGUES

_LOGGER = logging.getLogger(__name__)

STYLES = frozenset({"auto", "premier", "laliga", "bundesliga", "champions", "seriea"})
VIEWS = frozenset({"overview", "live", "fixtures", "results", "table",
                   "leaders", "clubs", "news", "settings"})
DEFAULT_UI = {"tab": "overview", "league": "all", "style": "auto", "revision": 0}
MAX_USERS = 256


def _valid(value: object) -> dict:
    """Discard malformed/stale persisted settings, without exposing user IDs."""
    if not isinstance(value, dict):
        return dict(DEFAULT_UI)
    tab = value.get("tab")
    league = value.get("league")
    style = value.get("style")
    return {
        "tab": tab if isinstance(tab, str) and tab in VIEWS else "overview",
        "league": league if isinstance(league, str) and (league in LEAGUES or league == "all") else "all",
        "style": style if isinstance(style, str) and style in STYLES else "auto",
        "revision": value.get("revision") if type(value.get("revision")) is int and 0 <= value["revision"] < 2**53 else 0,
    }


class FootballUIState:
    """Server-authoritative UI settings, saved atomically before acknowledgment."""

    def __init__(self, hass):
        self._hass = hass
        self._store = Store(hass, 1, f"{DOMAIN}_ui_state")
        self._rows: dict[str, dict] = {}
        self._loaded = False
        self._lock = asyncio.Lock()

    async def _load(self):
        if self._loaded:
            return
        stored = await self._store.async_load()
        users = stored.get("users", {}) if isinstance(stored, dict) else {}
        if isinstance(users, dict):
            self._rows = {user: _valid(values) for user, values in list(users.items())[:MAX_USERS]
                          if isinstance(user, str) and 0 < len(user) <= 128}
        self._loaded = True
        _LOGGER.debug("Football News server UI state loaded: users=%d", len(self._rows))

    async def read(self, user_id: str) -> dict:
        async with self._lock:
            await self._load()
            return dict(self._rows.get(user_id, DEFAULT_UI))

    async def update(self, user_id: str, changes: dict) -> dict:
        """Field-level patch prevents independent tabs from resetting other fields."""
        if not user_id:
            raise ValueError("Authenticated Home Assistant account required")
        for name, value in changes.items():
            if (name == "tab" and value not in VIEWS or
                name == "style" and value not in STYLES or
                name == "league" and value != "all" and value not in LEAGUES or
                name not in {"tab", "league", "style"}):
                raise ValueError("Invalid dashboard setting")
        if not changes:
            raise ValueError("No dashboard settings supplied")
        async with self._lock:
            await self._load()
            before = self._rows.get(user_id, DEFAULT_UI)
            proposed = {**before, **changes}
            if any(before.get(key) != value for key, value in changes.items()):
                if user_id not in self._rows and len(self._rows) >= MAX_USERS:
                    raise ValueError("Too many dashboard profiles")
                proposed["revision"] = before["revision"] + 1
                # Store is the commit point. Failed disk writes do not mutate RAM.
                new_rows = {**self._rows, user_id: proposed}
                await self._store.async_save({"users": new_rows})
                self._rows = new_rows
                # No account IDs or settings in system-wide event payload.
                self._hass.bus.async_fire(f"{DOMAIN}_ui_state_updated")
                _LOGGER.debug("Football News UI state saved: revision=%d fields=%s",
                              proposed["revision"], ",".join(sorted(changes)))
            return dict(proposed)
