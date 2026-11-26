"""Production WS restores HA Store rows even if coordinator feeds are empty."""
from __future__ import annotations

import unittest
from types import SimpleNamespace
from datetime import datetime, timezone
from test_cold_start_cache import (
    FakeStore, Cold, entry, document, bare_websocket_data_handler,
)

class FirstOpenDiskFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_ws_returns_saved_table_when_coordinator_has_empty_timestamped_feeds(self):
        FakeStore.documents.clear()
        FakeStore.documents['football_news_cache_abc'] = document()
        entry_ = entry()
        now=datetime.now(timezone.utc).isoformat()
        class Coordinator:
            data = {'fixtures': [], 'standings': [], 'news': [],
                    'updated_at': {'fixtures': now, 'standings': now, 'news': now}}
            _last_errors = []
            _attempted_refresh = True
            async def async_restore_cache(self): pass
        entry_.runtime_data={'coordinator':Coordinator(), 'entry': entry_}
        class ConfigEntries:
            def async_entries(self, _): return [entry_]
        class Prefs:
            async def read(self): return {'clubs': [], 'matches': [], 'leagues': []}
        class Connection:
            user=SimpleNamespace(is_admin=True, id='user')
            def send_result(self, id, value): self.data=value
        hass=SimpleNamespace(is_running=True, config_entries=ConfigEntries(), data={
            'football_news': {'entries': {'abc':entry_.runtime_data},
                              'cold_cache':Cold.FootballColdStartCache(object()),
                              'preferences':Prefs()}})
        connection=Connection()
        await bare_websocket_data_handler()(hass,connection,{'id':1})
        row=connection.data['leagues'][0]
        self.assertTrue(row['ready'])
        self.assertTrue(row['runtime_loaded'])
        self.assertEqual(row['fixtures'][0]['id'],'match')
        self.assertEqual(row['standings'][0]['name'],'Arsenal')
        self.assertEqual(row['cache_info']['restored_datasets'],['fixtures','standings'])
        self.assertEqual(connection.data['standings'][0]['name'],'Arsenal')

if __name__=='__main__': unittest.main()
