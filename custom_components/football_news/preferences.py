"""Small persistent, on-demand preferences shared by Football News entries."""
from __future__ import annotations

import asyncio
from homeassistant.helpers.storage import Store

from .const import DOMAIN


class FootballPreferences:
    """Store club favourites and pinned leagues, never access network."""

    def __init__(self, hass):
        self._hass = hass
        self._store = Store(hass, 1, f"{DOMAIN}_preferences")
        self._data = {"clubs": [], "leagues": [], "matches": []}
        self._loaded = False
        self._lock = asyncio.Lock()

    async def read(self) -> dict:
        async with self._lock:
            await self._load()
            return {name: [dict(x) if isinstance(x, dict) else x for x in values]
                    for name, values in self._data.items()}

    async def _load(self):
        if not self._loaded:
            stored = await self._store.async_load()
            if isinstance(stored, dict):
                for key in self._data:
                    if isinstance(stored.get(key), list):
                        self._data[key] = stored[key][:100]
            self._loaded = True
            self._hass.bus.async_fire(f"{DOMAIN}_preferences_updated")

    async def toggle_club(self, league: str, team_id: str, name: str):
        if not team_id.isascii() or not team_id.isdigit() or len(team_id) > 16:
            raise ValueError("Invalid team ID")
        if len(name.strip()) > 100 or not name.strip():
            raise ValueError("Invalid club name")
        async with self._lock:
            await self._load()
            clubs = self._data["clubs"]
            found = next((club for club in clubs if club["id"] == team_id and club["league"] == league), None)
            if found:
                clubs.remove(found)
            elif len(clubs) >= 5:
                raise ValueError("Maximum 5 favourite clubs")
            else:
                clubs.append({"league": league, "id": team_id, "name": name.strip()})
            await self._store.async_save(self._data)
            self._hass.bus.async_fire(f"{DOMAIN}_preferences_updated")
            return [dict(x) for x in clubs]

    async def set_club(self, league: str, team_id: str, name: str, enabled: bool) -> dict:
        """Idempotent save: retries and double taps cannot unexpectedly unstar a club."""
        if not isinstance(team_id, str) or not team_id.isascii() or not team_id.isdigit() or len(team_id) > 16:
            raise ValueError("Invalid team ID")
        if enabled and (not isinstance(name, str) or not name.strip() or len(name.strip()) > 100):
            raise ValueError("Invalid club name")
        async with self._lock:
            await self._load()
            clubs = self._data["clubs"]
            existing = next((club for club in clubs if club.get("id") == team_id and club.get("league") == league), None)
            changed = False
            if enabled and existing is None:
                if len(clubs) >= 5:
                    raise ValueError("Maximum 5 favourite clubs")
                clubs.append({"league": league, "id": team_id, "name": name.strip()})
                changed = True
            elif not enabled and existing is not None:
                clubs.remove(existing)
                changed = True
            elif enabled and existing is not None and existing.get("name") != name.strip():
                existing["name"] = name.strip()
                changed = True
            if changed:
                await self._store.async_save(self._data)
                self._hass.bus.async_fire(f"{DOMAIN}_preferences_updated")
            return {"clubs": [dict(club) for club in clubs], "saved": True,
                    "enabled": enabled, "changed": changed}

    async def toggle_league(self, league: str):
        async with self._lock:
            await self._load()
            items = self._data["leagues"]
            if league in items:
                items.remove(league)
            else:
                items.append(league)
            await self._store.async_save(self._data)
            self._hass.bus.async_fire(f"{DOMAIN}_preferences_updated")
            return list(items)

    async def toggle_match(self, league: str, event_id: str):
        if not event_id.isascii() or not event_id.isdigit() or len(event_id) > 24:
            raise ValueError("Invalid fixture ID")
        value = f"{league}:{event_id}"
        async with self._lock:
            await self._load()
            items = self._data["matches"]
            if value in items:
                items.remove(value)
            else:
                items.append(value)
                self._data["matches"] = items[-200:]
            await self._store.async_save(self._data)
            self._hass.bus.async_fire(f"{DOMAIN}_preferences_updated")
            return list(self._data["matches"])
