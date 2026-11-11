"""Defensive async ESPN adapter (public, undocumented upstream endpoints)."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Any

import aiohttp
from .const import API_ROOT
from .models import normalize_fixture, normalize_standings, normalize_news

_LOGGER = logging.getLogger(__name__)


class ProviderError(Exception):
    """Network or invalid upstream provider response."""


class FootballProvider:
    """Request only required datasets with a single shared HA HTTP session."""

    def __init__(self, session: aiohttp.ClientSession, league: str):
        self.session = session
        self.league = league
        self._cached: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    async def _json(self, path: str, params: dict | None = None) -> dict:
        url = f"{API_ROOT}/{path}"
        try:
            async with self.session.get(
                url, params=params, timeout=aiohttp.ClientTimeout(total=12),
                headers={"Accept": "application/json", "User-Agent": "FootballNews-HA/1.0"},
            ) as response:
                if response.status != 200:
                    raise ProviderError(f"HTTP {response.status} at {path.split('?')[0]}")
                data = await response.json(content_type=None)
                if not isinstance(data, dict):
                    raise ProviderError(f"Unexpected JSON format at {path}")
                return data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise ProviderError(f"Request failed at {path}: {type(err).__name__}") from err

    async def cached(self, key: str, ttl: int, factory):
        """Single-flight cache: exceptions never erase known-good content."""
        value = self._cached.get(key)
        if value and monotonic() - value[0] < ttl:
            return value[1]
        async with self._locks.setdefault(key, asyncio.Lock()):
            value = self._cached.get(key)
            if value and monotonic() - value[0] < ttl:
                return value[1]
            try:
                result = await factory()
            except ProviderError:
                # Let the coordinator keep last-good data WITHOUT falsifying its
                # last-success timestamp. A failed fetch must remain visible.
                if value is not None:
                    _LOGGER.warning("Upstream %s failed; retaining prior coordinator snapshot", key)
                raise
            self._cached[key] = (monotonic(), result)
            return result

    async def fixtures(self) -> list[dict]:
        now = datetime.now(timezone.utc)
        start = (now - timedelta(days=2)).strftime("%Y%m%d")
        end = (now + timedelta(days=8)).strftime("%Y%m%d")
        async def fetch():
            data = await self._json(f"site/v2/sports/soccer/{self.league}/scoreboard", {"dates": f"{start}-{end}", "limit": 300})
            events = data.get("events")
            if not isinstance(events, list):
                raise ProviderError("Scoreboard response has no events array")
            return [result for event in events if isinstance(event, dict) if (result := normalize_fixture(event, self.league)) is not None]
        return await self.cached(f"fixtures:{start}:{end}", 60, fetch)

    async def standings(self) -> list[dict]:
        async def fetch():
            data = await self._json(f"v2/sports/soccer/{self.league}/standings")
            if not isinstance(data.get("children"), list) and not isinstance(data.get("standings"), dict):
                raise ProviderError("Standings response has no standings content")
            return normalize_standings(data)
        return await self.cached("standings", 6 * 3600, fetch)

    async def news(self) -> list[dict]:
        async def fetch():
            data = await self._json(f"site/v2/sports/soccer/{self.league}/news", {"limit": 15})
            if not isinstance(data.get("articles"), list):
                raise ProviderError("News response has no articles array")
            return normalize_news(data, self.league)
        return await self.cached("news", 30 * 60, fetch)

    async def summary(self, event_id: str) -> dict:
        # Strictly restrict to ESPN numeric event identifiers.
        if not event_id.isascii() or not event_id.isdigit() or len(event_id) > 24:
            raise ProviderError("Invalid event identifier")
        return await self._json(f"site/v2/sports/soccer/{self.league}/summary", {"event": event_id})
