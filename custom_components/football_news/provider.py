"""Defensive async ESPN adapter (public, undocumented upstream endpoints)."""
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timedelta, timezone
from time import monotonic
from typing import Any

import aiohttp
from .const import API_ROOT, season_year_for_league
from .espn_site_stats import parse_espn_stats_html
from .models import (normalize_fixture, normalize_standings, normalize_news,
                     normalize_club, normalize_roster, normalize_leaders, normalize_teams)

_LOGGER = logging.getLogger(__name__)
_REQUEST_LIMIT = asyncio.Semaphore(4)


class ProviderError(Exception):
    """Network or invalid upstream provider response."""


class FootballProvider:
    """Request only required datasets with a single shared HA HTTP session."""

    def __init__(self, session: aiohttp.ClientSession, league: str):
        self.session = session
        self.league = league
        self._cached: dict[str, tuple[float, Any]] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._leader_error_at: float = 0
        self._leader_error: str = ""

    async def _json(self, path: str, params: dict | None = None) -> dict:
        url = f"{API_ROOT}/{path}"
        try:
            async with _REQUEST_LIMIT:
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

    @staticmethod
    def _months_between(start: datetime, end: datetime) -> list[str]:
        """Enumerate at most the calendar months that intersect a bounded window."""
        months = []
        year, month = start.year, start.month
        while (year, month) <= (end.year, end.month):
            months.append(f"{year:04d}{month:02d}")
            year, month = (year + 1, 1) if month == 12 else (year, month + 1)
        return months

    async def _month_events(self, yyyymm: str) -> list[dict]:
        """Request ESPN's supported six-digit calendar filter, shared by both views.

        In recent ESPN deployments date *ranges* return HTTP 400. This query
        deliberately uses YYYYMM; invalid envelopes and HTTP errors do not
        masquerade as an empty month of matches.
        """
        now = datetime.now(timezone.utc)
        year, month = int(yyyymm[:4]), int(yyyymm[4:])
        age_months = (now.year - year) * 12 + now.month - month
        ttl = 120 if age_months == 0 else (21600 if age_months > 0 else 900)

        async def fetch():
            data = await self._json(
                f"site/v2/sports/soccer/{self.league}/scoreboard",
                {"dates": yyyymm, "limit": 500},
            )
            if not isinstance(data.get("events"), list):
                raise ProviderError(f"Scoreboard {yyyymm}: events array missing")
            items = self._clean_fixtures(data["events"])
            # When a provider returns extra neighbouring dates, do not invent
            # an inaccurate selected-month result.
            return [item for item in items if item.get("kickoff", "")[:7].replace("-", "") == yyyymm]

        return await self.cached(f"month:{yyyymm}", ttl, fetch)

    async def fixtures(self) -> list[dict]:
        """Load the 14-day history plus 35-day outlook by *calendar month*.

        The full window spans up to three months, with single-flight cache per
        calendar month and bounded concurrency. A partial outage preserves
        successfully fetched months; a total outage raises ProviderError so
        the coordinator keeps its last-good snapshot.
        """
        now = datetime.now(timezone.utc)
        start, end = now - timedelta(days=14), now + timedelta(days=35)
        months = self._months_between(start, end)
        results = await asyncio.gather(
            *(self._month_events(month) for month in months), return_exceptions=True
        )
        matches = []
        failures = []
        for month, result in zip(months, results, strict=True):
            if isinstance(result, Exception):
                failures.append(f"{month}: {result}")
            else:
                matches.extend(result)
        if failures:
            _LOGGER.warning("Football News %s calendar months failed: %s",
                            self.league, "; ".join(failures)[:400])
        if len(failures) == len(months):
            raise ProviderError("All calendar months failed: " + "; ".join(failures)[:300])
        # Match time is UTC; allow matches on either boundary day, not a strict
        # hour-to-hour cutoff that hides completed fixtures earlier today.
        start_day, end_day = start.date().isoformat(), end.date().isoformat()
        return self._clean_fixtures_raw(matches, start_day, end_day)

    @staticmethod
    def _clean_fixtures_raw(matches: list[dict], start_day: str, end_day: str) -> list[dict]:
        unique = {item["id"]: item for item in matches
                  if start_day <= item.get("kickoff", "")[:10] <= end_day}
        return sorted(unique.values(), key=lambda item: item.get("kickoff") or "")[:400]

    def _clean_fixtures(self, events: list) -> list[dict]:
        """Deduplicate ESPN events, then sort in kickoff order."""
        unique = {}
        for event in events:
            if isinstance(event, dict):
                item = normalize_fixture(event, self.league)
                if item is not None:
                    unique[item["id"]] = item
        return sorted(unique.values(), key=lambda item: item.get("kickoff") or "")[:400]

    async def teams(self) -> list[dict]:
        """Load the competition's team directory on demand, not at HA startup."""
        async def fetch():
            data = await self._json(f"site/v2/sports/soccer/{self.league}/teams", {"limit": 100})
            teams = normalize_teams(data)
            if not teams:
                raise ProviderError("Team directory is absent or empty")
            return teams
        return await self.cached("teams", 12 * 3600, fetch)

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

    async def club(self, team_id: str) -> dict:
        if not team_id.isascii() or not team_id.isdigit() or len(team_id) > 16:
            raise ProviderError("Invalid team identifier")
        async def fetch():
            return normalize_club(await self._json(f"site/v2/sports/soccer/{self.league}/teams/{team_id}"), self.league)
        return await self.cached(f"club:{team_id}", 24 * 3600, fetch)

    async def roster(self, team_id: str) -> list[dict]:
        if not team_id.isascii() or not team_id.isdigit() or len(team_id) > 16:
            raise ProviderError("Invalid team identifier")
        async def fetch():
            return normalize_roster(await self._json(f"site/v2/sports/soccer/{self.league}/teams/{team_id}/roster"))
        return await self.cached(f"roster:{team_id}", 12 * 3600, fetch)

    def _season_year(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        # Domestic European leagues start in summer. MLS, Brazil, Ireland and
        # international tournaments use their calendar competition year.
        return season_year_for_league(self.league, now)

    async def leaders(self) -> list[dict]:
        """Read goal/assist leaders on demand from supported ESPN endpoints.

        Score categories and athlete references must be supplied by ESPN. Never
        calculate league-wide top scorers from a partial match window.
        """
        # Failure cooldown prevents repeated frontend views from hammering
        # undocumented upstream endpoints. Successful cache is 6 hours.
        if self._leader_error_at and monotonic() - self._leader_error_at < 120:
            raise ProviderError(self._leader_error or "Leader source temporarily unavailable")
        async def fetch():
            now = datetime.now(timezone.utc)
            # European competitions generally use the starting calendar year of
            # their season (2026/27 => 2026). Jan-Jun belongs to prior season.
            season = self._season_year(now)
            core = "https://sports.core.api.espn.com/v2/sports/soccer/leagues/" + self.league
            # Season-specific Core leaders are preferred over all-season feeds.
            # ESPN JSON interfaces are public but undocumented and may change.
            # Avoid scraping www.espn.com pages protected by browser challenges.
            sources = (
                (f"{core}/seasons/{season}/types/2/leaders", {}),
                (f"{core}/seasons/{season}/leaders", {}),
                (f"{core}/leaders", {}),
                (f"{API_ROOT}/v2/sports/soccer/{self.league}/leaders", {}),
            )
            errors = []
            result_rows: dict[tuple[str, str], dict] = {}
            throttled = False
            for index, (url, params) in enumerate(sources):
                # Full Players view needs up to Top 15 for BOTH scoring and
                # assists. Continue only while those lists are incomplete.
                if index >= 2 and all(sum(row[0] == cat for row in result_rows) >= 15
                                      for cat in ("goals", "assists")):
                    break
                try:
                    data = await self._absolute_json(url, params)
                    if url.startswith("https://sports.core.api.espn.com/"):
                        data = await self._resolve_core_leaders(data)
                    rows = normalize_leaders(data)
                    for row in rows:
                        key = (row["category"], row["player"].strip().casefold())
                        if key not in result_rows or row["value"] > result_rows[key]["value"]:
                            result_rows[key] = row
                    if rows:
                        _LOGGER.info("ESPN leaders league=%s season=%s source=%s categories=%s rows=%d",
                                     self.league, season, url.split('/')[2],
                                     sorted({r['category'] for r in rows}), len(rows))
                        # Continue through league-wide ESPN leader feeds to fill
                        # missing categories. Never synthesize top-N from partial
                        # per-athlete or single-match samples.
                        counts = {cat: sum(r["category"] == cat for r in result_rows.values())
                                  for cat in ("goals", "assists", "yellow_cards", "red_cards")}
                        # Avoid extra requests once both full Top 15 lists are
                        # present; the Overview still shows only the first 3.
                        if counts["goals"] >= 15 and counts["assists"] >= 15:
                            break
                    else:
                        errors.append(f"{url.split('/')[2]}: unrecognized leaderboard JSON")
                except ProviderError as err:
                    errors.append(f"{url.split('/')[2]}: {str(err)[:65]}")
                    if "HTTP 429" in str(err) or "HTTP 403" in str(err):
                        throttled = True
                        break  # honor ESPN rate limits / access restrictions
            # Normal public ESPN stats pages can contain server-rendered tables.
            # A robot check, HTTP 403, or JavaScript-only page is NOT bypassed.
            if not throttled and any(sum(row[0] == cat for row in result_rows) < 15
                                     for cat in ("goals", "assists")):
                try:
                    site_rows = await self._site_stats_html(season)
                    for row in site_rows:
                        key = (row["category"], row["player"].strip().casefold())
                        if key not in result_rows:
                            result_rows[key] = row
                except ProviderError as error:
                    errors.append(f"www.espn.com: {str(error)[:65]}")
            if result_rows:
                return sorted(result_rows.values(), key=lambda r: (r['category'], -r['value'], r['player']))
            _LOGGER.warning("ESPN leaders unavailable league=%s season=%s throttled=%s attempts=%s",
                            self.league, season, throttled, "; ".join(errors)[:320])
            raise ProviderError("ESPN season rankings unavailable: " + "; ".join(errors)[:260])
        cache_key = "leaders:" + str(self._season_year())
        try:
            result = await self.cached(cache_key, 6*3600, fetch)
            self._leader_error_at = 0
            self._leader_error = ""
            return result
        except ProviderError as err:
            self._leader_error_at = monotonic()
            self._leader_error = str(err)[:220]
            raise

    async def _site_stats_html(self, season: int) -> list[dict]:
        """Read ESPN's publicly rendered tables, only if the site permits access.

        No login, proxy, challenge solving or embedded script execution.
        """
        if not (2000 <= season <= 2100):
            raise ProviderError("Invalid ESPN season")
        url = ("https://www.espn.com/soccer/stats/_/league/"
               f"{self.league}/season/{season}")
        try:
            async with _REQUEST_LIMIT:
                async with self.session.get(
                    url, timeout=aiohttp.ClientTimeout(total=7),
                    headers={"Accept": "text/html", "User-Agent": "FootballNews-HA/1.0"},
                ) as response:
                    if response.status != 200:
                        raise ProviderError(f"HTTP {response.status} at ESPN public stats")
                    if "html" not in response.headers.get("Content-Type", ""):
                        raise ProviderError("ESPN stats page is not HTML")
                    if response.content_length and response.content_length > 2_500_000:
                        raise ProviderError("ESPN stats page exceeds size limit")
                    html = await response.text(errors="replace")
                    if len(html) > 2_500_000:
                        raise ProviderError("ESPN stats page exceeds size limit")
                    if "verify that you're not a robot" in html.casefold():
                        raise ProviderError("ESPN site requires browser verification")
                    return parse_espn_stats_html(html)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise ProviderError(f"ESPN stats page unavailable: {type(err).__name__}") from err

    async def _resolve_core_leaders(self, payload: dict) -> dict:
        """Resolve ESPN Core reference objects with a bounded concurrent batch.

        Core sometimes embeds a `$ref` rather than a player name. Sequential
        lookups across 20 athletes can exceed the HA frontend WebSocket timeout.
        Expand up to fifteen athletes for scoring/assists and at most five for
        other categories. Bounded concurrent requests never block HA startup.
        """
        groups = payload.get("categories") or payload.get("items")
        if not isinstance(groups, list):
            return payload
        data = {**payload, "categories": groups} if "categories" not in payload else payload
        base = ("https://sports.core.api.espn.com/v2/sports/soccer/leagues/"
                f"{self.league}/")
        # Core can use either a league-level or season-scoped athlete reference.
        allowed = re.compile(re.escape(base) +
            r"(?:seasons/[0-9]{4}/)?(?:athletes|teams)/[0-9]{1,18}"
            r"(?:\?[a-zA-Z0-9=&_%-]+)?$")
        targets: dict[str, list[tuple[dict, str]]] = {}
        for group in groups[:18]:
            if not isinstance(group, dict):
                continue
            records = group.get("leaders") or group.get("entries") or []
            if not isinstance(records, list):
                continue
            label=str(group.get("name") or group.get("displayName") or "").casefold()
            max_rows=15 if ("goal" in label or "scor" in label or "assist" in label) else 5
            for record in records[:max_rows]:
                if not isinstance(record, dict):
                    continue
                for field in ("athlete", "team"):
                    obj = record.get(field)
                    if not isinstance(obj, dict):
                        continue
                    ref = obj.get("$ref")
                    if isinstance(ref, str) and allowed.fullmatch(ref):
                        # ESPN sometimes embeds displayName and a reference but
                        # omits id/headshot. The permitted reference itself holds
                        # the athlete ID; no extra network request is required.
                        if field == "athlete" and not obj.get("id"):
                            obj["id"] = ref.split("?", 1)[0].rsplit("/", 1)[-1]
                        if obj.get("displayName") or obj.get("fullName"):
                            continue
                        targets.setdefault(ref, []).append((record, field))
                    elif isinstance(ref, str) and not (obj.get("displayName") or obj.get("fullName")):
                        # Discard untrusted/unsupported URLs entirely.
                        record[field] = {}
        # Do not resolve more than thirty references or wait indefinitely.
        # Names embedded in ESPN leader rows require no extra requests.
        targets = dict(list(targets.items())[:30])
        local_limit = asyncio.Semaphore(6)
        async def read_ref(url: str):
            async with local_limit:
                try:
                    return url, await self._absolute_json(url)
                except ProviderError as error:
                    _LOGGER.debug("ESPN leader reference unavailable league=%s: %s",
                                  self.league, type(error).__name__)
                    return url, {}
        if targets:
            jobs=[asyncio.create_task(read_ref(url)) for url in targets]
            done, pending = await asyncio.wait(jobs, timeout=10)
            for job in pending:
                job.cancel()
            if pending:
                await asyncio.gather(*pending,return_exceptions=True)
            results=[job.result() for job in done if not job.cancelled() and not job.exception()]
            for url, resolved in results:
                if not isinstance(resolved, dict):
                    continue
                for record, field in targets[url]:
                    if resolved.get("displayName") or resolved.get("fullName") or resolved.get("name"):
                        record[field] = resolved
        return data

    async def _absolute_json(self, url: str, params: dict | None = None) -> dict:
        """Use only two known HTTPS ESPN hosts for player leader feeds."""
        if not any(url.startswith(prefix) for prefix in (
            "https://site.web.api.espn.com/apis/common/v3/sports/soccer/",
            f"{API_ROOT}/v2/sports/soccer/",
            "https://sports.core.api.espn.com/v2/sports/soccer/leagues/",
        )):
            raise ProviderError("Unsupported leader API host")
        try:
            async with _REQUEST_LIMIT:
                async with self.session.get(url, params=params,
                    timeout=aiohttp.ClientTimeout(total=6),
                    headers={"Accept": "application/json", "User-Agent": "FootballNews-HA/1.0"}) as response:
                    if response.status != 200:
                        raise ProviderError(f"HTTP {response.status} at leaders")
                    data = await response.json(content_type=None)
                    if not isinstance(data, dict):
                        raise ProviderError("Unsupported leader JSON")
                    return data
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            raise ProviderError(f"Leader feed failed: {type(err).__name__}") from err

    async def fixtures_month(self, month: str) -> list[dict]:
        """Fetch full month only when requested; never during HA startup."""
        if (len(month) != 7 or month[4] != "-" or
            not (month[:4] + month[5:]).isascii() or
            not (month[:4] + month[5:]).isdigit()):
            raise ProviderError("Month must have the YYYY-MM format")
        year, number = int(month[:4]), int(month[5:])
        if not (2020 <= year <= 2100 and 1 <= number <= 12):
            raise ProviderError("Month out of supported range")
        return await self._month_events(f"{year:04d}{number:02d}")
