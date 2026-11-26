"""Regression: recover real HA Store caches even when league index is absent.

Uses FakeStore because this suite intentionally does not claim to run a Home
Assistant instance. Network requests are neither implemented nor allowed.
"""
import asyncio
import importlib.util
import tempfile
import sys
import types
from unittest.mock import patch
import unittest
from pathlib import Path
from types import SimpleNamespace

from test_cold_start_cache import BASE, PKG, FakeStore, document, bare_websocket_data_handler
from test_disk_cache import MockProvider, coordinator_module

spec = importlib.util.spec_from_file_location(PKG + '.recovery', BASE / 'recovery.py')
recovery_module = importlib.util.module_from_spec(spec)
modules = {
    'homeassistant': types.ModuleType('homeassistant'),
    'homeassistant.helpers': types.ModuleType('homeassistant.helpers'),
    'homeassistant.helpers.storage': types.ModuleType('homeassistant.helpers.storage'),
}
modules['homeassistant.helpers.storage'].Store = FakeStore
with patch.dict(sys.modules, modules):
    spec.loader.exec_module(recovery_module)
Recovery = recovery_module.FootballSavedCacheRecovery


class RecoveryFromMissingIndex(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        FakeStore.documents.clear()
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.storage = self.root / '.storage'
        self.storage.mkdir()
        self.hass = SimpleNamespace(
            config=SimpleNamespace(path=lambda name: str(self.root / name)),
            async_add_executor_job=lambda fun: asyncio.to_thread(fun),
        )

    async def test_existing_ha_cache_without_registry_returns_league_and_standings(self):
        FakeStore.documents['football_news_cache_abc'] = document()
        (self.storage / 'football_news_cache_abc').touch()
        finder = Recovery(self.hass)
        found = await finder.async_snapshots()
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0].data['league'], 'eng.1')
        self.assertEqual(found[0][1]['standings'][0]['name'], 'Arsenal')
        self.assertEqual(found[0][0].state, 'saved_cache_without_entry')
        # Not creating a new integration is important: read-only data only.
        self.assertFalse(hasattr(self.hass, 'config_entries'))

    async def test_production_ws_displays_ha_cache_after_both_indexes_disappear(self):
        FakeStore.documents['football_news_cache_abc'] = document()
        (self.storage / 'football_news_cache_abc').touch()
        class ConfigEntries:
            def async_entries(self, _domain): return []
        class Prefs:
            async def read(self): return {'clubs': [], 'matches': [], 'leagues': []}
        class Connection:
            user = SimpleNamespace(is_admin=True, id='test')
            def send_result(self, _id, result): self.result = result
        self.hass.is_running = True
        self.hass.config_entries = ConfigEntries()
        self.hass.data = {'football_news': {
            'entries': {}, 'preferences': Prefs(),
            'cold_cache': SimpleNamespace(async_entry_snapshot=lambda _entry: asyncio.sleep(0, result={})),
            'saved_cache_recovery': Recovery(self.hass),
        }}
        connection = Connection()
        await bare_websocket_data_handler()(self.hass, connection, {'id':1})
        self.assertEqual(connection.result['registry_source'], 'saved_cache_files')
        self.assertEqual(connection.result['recovery_status']['native_entries'], 0)
        self.assertEqual(connection.result['standings'][0]['name'], 'Arsenal')

    async def test_new_entry_can_reuse_older_entry_id_snapshot_if_empty(self):
        from test_cold_start_cache import entry, Cold
        FakeStore.documents['football_news_cache_old'] = document()
        (self.storage / 'football_news_cache_old').touch()
        new_entry = entry('new')
        class ConfigEntries:
            def async_entries(self, _domain): return [new_entry]
        class Prefs:
            async def read(self): return {'clubs': [], 'matches': [], 'leagues': []}
        class Connection:
            user = SimpleNamespace(is_admin=True, id='test')
            def send_result(self, _id, result): self.result = result
        self.hass.is_running = True
        self.hass.config_entries = ConfigEntries()
        self.hass.data = {'football_news': {'entries': {}, 'preferences': Prefs(),
            'cold_cache': Cold.FootballColdStartCache(object()),
            'saved_cache_recovery': Recovery(self.hass)}}
        connection = Connection()
        await bare_websocket_data_handler()(self.hass, connection, {'id':1})
        self.assertEqual(connection.result['leagues'][0]['entry_id'], 'new')
        self.assertEqual(connection.result['standings'][0]['name'], 'Arsenal')
        self.assertEqual(connection.result['backend_version'], '2026.11.20.4')

    async def test_rejects_foreign_invalid_and_stale_cache(self):
        FakeStore.documents['football_news_cache_bad'] = document(league='xxx')
        FakeStore.documents['football_news_cache_old'] = document(season=2025)
        (self.storage / 'football_news_cache_bad').touch()
        (self.storage / 'football_news_cache_old').touch()
        self.assertFalse(await Recovery(self.hass).async_snapshots())


class InterruptedCacheRead(unittest.IsolatedAsyncioTestCase):
    async def test_cancelled_restore_can_retry(self):
        from test_disk_cache import FakeStore
        FakeStore.documents.clear()
        FakeStore.documents['football_news_cache_restore'] = document()
        ready = asyncio.Event()
        original = FakeStore.async_load
        async def slow_read(store):
            await ready.wait()
            return await original(store)
        from unittest.mock import patch
        provider = MockProvider()
        hass = SimpleNamespace(async_create_task=lambda cor: asyncio.create_task(cor))
        entry = SimpleNamespace(entry_id='restore', options={})
        coordinator = coordinator_module.FootballNewsCoordinator(hass, entry, provider)
        with patch.object(FakeStore, 'async_load', slow_read):
            with self.assertRaises(asyncio.TimeoutError):
                await asyncio.wait_for(coordinator.async_restore_cache(), 0.01)
            self.assertFalse(coordinator._cache_loaded,
                             'A timeout must never permanently mark HA cache as loaded')
            ready.set()
            await coordinator.async_restore_cache()
        self.assertTrue(coordinator._cache_loaded)
        self.assertEqual(coordinator.data['standings'][0]['name'], 'Arsenal')

if __name__ == '__main__': unittest.main()
