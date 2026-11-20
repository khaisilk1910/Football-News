"""Read-only recovery of HA-managed football snapshots if the entry index is missing.

This is deliberately a *display* fallback, not config-entry recreation: users
must manage active integrations in Settings. Only the known football cache
namespace is scanned, and every payload is validated before it is shown.
"""
from __future__ import annotations

import asyncio
import logging
import re
from pathlib import Path
from time import monotonic
from types import SimpleNamespace

from homeassistant.helpers.storage import Store

from .const import DOMAIN, LEAGUES, season_year_for_league
from .disk_cache import validated_snapshot

_LOGGER = logging.getLogger(__name__)
_PREFIX = f"{DOMAIN}_cache_"
_VALID_ID = re.compile(r"[a-zA-Z0-9_-]{1,128}\Z")
_MAX_SAVED = 32


class FootballSavedCacheRecovery:
    """Find existing HA Store snapshots when both entry registries are empty."""

    def __init__(self, hass):
        self.hass = hass
        self._lock = asyncio.Lock()
        self._last_read = 0.0
        self._rows: list[tuple[object, dict]] = []

    def _keys_from_disk(self) -> list[str]:
        config = getattr(self.hass, 'config', None)
        if config is None or not callable(getattr(config, 'path', None)):
            return []
        storage = Path(config.path('.storage'))
        if not storage.is_dir():
            return []
        keys = []
        for path in storage.glob(f'{_PREFIX}*'):
            entry_id = path.name[len(_PREFIX):]
            if path.is_file() and _VALID_ID.fullmatch(entry_id):
                keys.append(path.name)
                if len(keys) >= _MAX_SAVED:
                    break
        return keys

    async def async_snapshots(self) -> list[tuple[object, dict]]:
        async with self._lock:
            if self._last_read and monotonic() - self._last_read < 30:
                return list(self._rows)
            executor = getattr(self.hass, 'async_add_executor_job', None)
            if not callable(executor):
                return []
            keys = await executor(self._keys_from_disk)
            async def read_candidate(key):
                try:
                    # Read HA-managed Store files, never raw JSON on the loop.
                    document = await asyncio.wait_for(Store(self.hass, 1, key).async_load(), timeout=3)
                    league = document.get('league') if isinstance(document, dict) else None
                    if league not in LEAGUES:
                        return None
                    valid = validated_snapshot(document, league, season=season_year_for_league(league))
                    datasets = valid.get('datasets') or {}
                    if not any(datasets.get(name) for name in ('fixtures', 'standings', 'news')):
                        return None
                    snapshot = {
                        **{name: datasets.get(name, []) for name in ('fixtures', 'standings', 'news')},
                        'updated_at': valid.get('updated_at', {}),
                        'league_logo': valid.get('league_logo', ''),
                        'cache_info': {'type':'disk', 'restored_datasets':sorted(datasets)},
                        'errors': [],
                    }
                    entry = SimpleNamespace(entry_id=key[len(_PREFIX):], data={'league':league},
                                            options={}, runtime_data=None,
                                            state='saved_cache_without_entry')
                    return entry, snapshot
                except (OSError, ValueError, TypeError, asyncio.TimeoutError) as error:
                    _LOGGER.warning('Football News saved-cache recovery failed error=%s', type(error).__name__)
                    return None

            limit = asyncio.Semaphore(6)
            async def bounded(key):
                async with limit:
                    return await read_candidate(key)

            discovered = await asyncio.gather(*(bounded(key) for key in keys))
            results = [result for result in discovered if result is not None]
            # Duplicate leagues may exist after a reconfiguration. Prefer the
            # most recently updated snapshot, without exposing config IDs.
            results.sort(key=lambda pair:max(pair[1].get('updated_at', {}).values(), default=''), reverse=True)
            seen = set()
            self._rows = [(entry, snapshot) for entry, snapshot in results
                          if not (entry.data['league'] in seen or seen.add(entry.data['league']))]
            self._last_read = monotonic()
            if self._rows:
                _LOGGER.warning('Football News restored %d saved league(s) with no HA config entries; '
                                'these are read-only snapshots until the integration is configured',
                                len(self._rows))
            return list(self._rows)
