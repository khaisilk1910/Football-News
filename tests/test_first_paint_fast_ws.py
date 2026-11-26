"""Fast bootstrap must never block on HA Store, registry or ESPN."""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from test_cold_start_cache import bare_websocket_data_handler, entry


class FirstPaintTests(unittest.IsolatedAsyncioTestCase):
    async def test_reload_uses_coordinator_memory_without_store_wait(self):
        competition = entry('abc')
        coordinator = SimpleNamespace(
            data={'fixtures':[{'id':'m01', 'state':'pre', 'home':{'name':'Arsenal'},
                               'away':{'name':'Chelsea'}}],
                  'standings':[{'name':'Arsenal', 'position':1, 'points':12}],
                  'updated_at':{'fixtures':'2026-11-21T05:00:00+00:00'}},
            _last_errors=[], _attempted_refresh=True,
        )
        runtime = {'coordinator': coordinator, 'entry':competition}
        competition.runtime_data = runtime
        class Entries:
            def async_entries(self, domain):
                self.domain = domain
                return [competition]
        class Unavailable:
            async def read(self, *_):
                await asyncio.Event().wait()
            async def async_entry_snapshot(self, _):
                raise AssertionError('fast WebSocket must not wait for disk')
            async def fallback_entries(self):
                raise AssertionError('fast WebSocket must not inspect registry')
            async def async_snapshots(self):
                raise AssertionError('fast WebSocket must not scan storage')
        class Connection:
            user=SimpleNamespace(id='test', is_admin=True)
            def send_result(self, _id, result): self.result=result
        slow = Unavailable()
        hass=SimpleNamespace(is_running=True, config_entries=Entries(),data={
            'football_news':{'entries':{'abc':runtime},'cold_cache':slow,
                             'preferences':slow,'ui_state':slow,'league_registry':slow,
                             'saved_cache_recovery':slow}})
        conn=Connection()
        await asyncio.wait_for(bare_websocket_data_handler()(hass,conn,{'id':1,'fast':True}),timeout=0.1)
        self.assertTrue(conn.result['bootstrap_partial'])
        self.assertEqual(conn.result['leagues'][0]['fixtures'][0]['id'],'m01')
        self.assertEqual(conn.result['leagues'][0]['standings'][0]['name'],'Arsenal')
        self.assertEqual(conn.result['backend_version'],'2026.11.20.4')  # AST harness default

    async def test_first_open_without_loaded_entries_still_answers_immediately(self):
        class Entries:
            def async_entries(self, domain): return []
        class Connection:
            user=None
            def send_result(self, _id, result): self.result=result
        hass=SimpleNamespace(is_running=True,config_entries=Entries(),data={
            'football_news':{'entries':{}}})
        conn=Connection()
        await asyncio.wait_for(bare_websocket_data_handler()(hass,conn,{'id':1,'fast':True}),timeout=0.1)
        self.assertEqual(conn.result['configured_count'],0)
        self.assertEqual(conn.result['leagues'],[])
        self.assertTrue(conn.result['bootstrap_partial'])

if __name__=='__main__': unittest.main()
