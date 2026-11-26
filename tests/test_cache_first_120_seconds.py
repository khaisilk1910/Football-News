"""Cache-first 120s grace, persistent HA Store fallback, no upstream I/O."""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from test_cold_start_cache import Cold, FakeStore, bare_websocket_data_handler, document, entry
from test_disk_cache import MockProvider, coordinator_module


class FirstVisitSavedCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.documents.clear()
        FakeStore.writes.clear()

    async def test_fast_first_open_reads_existing_store_without_ram_or_espn(self):
        FakeStore.documents['football_news_cache_abc'] = document()
        league_entry = entry()
        class Entries:
            def async_entries(self, _): return [league_entry]
        class Connection:
            user = SimpleNamespace(id='user', is_admin=False)
            def send_result(self, _id, value): self.result = value
        hass = SimpleNamespace(is_running=True, config_entries=Entries(), data={
            'football_news': {'entries': {}, 'cold_cache': Cold.FootballColdStartCache(object())}})
        conn = Connection()
        await bare_websocket_data_handler()(hass, conn, {'id':1,'fast':True})
        self.assertEqual(conn.result['leagues'][0]['fixtures'][0]['id'], 'match', 'first response must read durable HA Store')
        self.assertTrue(conn.result['bootstrap_partial'])
        full=Connection()
        await bare_websocket_data_handler()(hass,full,{'id':2})
        self.assertEqual(full.result['leagues'][0]['fixtures'][0]['id'], 'match')
        self.assertEqual(full.result['leagues'][0]['standings'][0]['name'], 'Arsenal')
        self.assertEqual(full.result['cache_state'], 'available')

    async def test_first_install_with_no_store_returns_explicit_empty_state(self):
        league_entry=entry()
        class Entries:
            def async_entries(self, _): return [league_entry]
        class Connection:
            user=None
            def send_result(self, _id, value): self.result=value
        hass=SimpleNamespace(is_running=True, config_entries=Entries(),data={
            'football_news':{'entries':{},'cold_cache':Cold.FootballColdStartCache(object())}})
        connection=Connection()
        await bare_websocket_data_handler()(hass,connection,{'id':12,'fast':True})
        self.assertEqual(connection.result['cache_state'],'restoring')
        self.assertEqual(connection.result['configured_count'],1)
        self.assertEqual(connection.result['leagues'][0]['fixtures'],[])

    async def test_no_config_registry_quickly_recovers_valid_saved_cache(self):
        FakeStore.documents['football_news_cache_abc'] = document()
        saved=entry()
        class Entries:
            def async_entries(self, _): return []
        class Recovery:
            async def async_snapshots(self):
                return [(saved, {'fixtures':[{'id':'stored','state':'pre'}],
                                 'standings':[{'name':'Arsenal','position':1,'points':3}],
                                 'updated_at':{'fixtures':'2026-11-21T00:00:00+00:00'},
                                 'cache_info':{'type':'disk','restored_datasets':['fixtures']}})]
        class Connection:
            user=None
            def send_result(self, _id, value): self.result=value
        hass=SimpleNamespace(is_running=True,config_entries=Entries(),data={
            'football_news':{'entries':{},'saved_cache_recovery':Recovery(),
                             'cold_cache':Cold.FootballColdStartCache(object())}})
        connection=Connection()
        await bare_websocket_data_handler()(hass,connection,{'id':13,'fast':True})
        self.assertEqual(connection.result['cache_state'],'available')
        full=Connection()
        await bare_websocket_data_handler()(hass,full,{'id':14})
        self.assertEqual(full.result['cache_state'],'available')
        self.assertEqual(full.result['leagues'][0]['fixtures'][0]['id'],'match', 'native HA Store snapshot takes priority over recovery mirror')


class GracePeriodTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.documents.clear()
        FakeStore.writes.clear()
        self.hass=SimpleNamespace(
            async_create_task=lambda coro:asyncio.create_task(coro),
            bus=SimpleNamespace(async_fire=lambda *a:None))

    async def test_first_two_minutes_do_not_request_espn_and_then_resume(self):
        provider=MockProvider()
        ent=SimpleNamespace(entry_id='abc',options={})
        c=coordinator_module.FootballNewsCoordinator(self.hass,ent,provider)
        c.begin_cache_first_window(120)
        before=c.espn_wait_seconds()
        self.assertGreaterEqual(before,119)
        cache=await c._async_update_data()
        self.assertEqual(cache['fixtures'],[])
        self.assertEqual(provider.calls,0)
        self.assertFalse(c._attempted_refresh)
        c.note_panel_visit()
        self.assertGreaterEqual(c.espn_wait_seconds(),119)
        hold=c._espn_hold_until
        c.note_panel_visit()
        self.assertEqual(c._espn_hold_until,hold,'reload must not restart timer')
        c._espn_hold_until=0
        fresh=await c._async_update_data()
        self.assertEqual(provider.calls,1)
        self.assertEqual(fresh['fixtures'][0]['id'],'f1')
        self.assertTrue(c._attempted_refresh)

    async def test_prior_successful_refresh_not_paused_by_panel_reload(self):
        c=coordinator_module.FootballNewsCoordinator(
            self.hass,SimpleNamespace(entry_id='abc',options={}),MockProvider())
        c.begin_cache_first_window(0)
        await c._async_update_data()
        c.note_panel_visit()
        self.assertEqual(c.espn_wait_seconds(),0)


if __name__=='__main__':
    unittest.main()
