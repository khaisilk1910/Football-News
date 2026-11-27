"""First-view disk behavior, partial registry and multi-league cache recovery."""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from test_cold_start_cache import Cold, FakeStore, Snapshot, document, entry
from _football_news_disk_test.store_first import async_store_first_snapshot


class StoreRecoveryRegression(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.documents.clear()
        FakeStore.writes.clear()

    async def test_forced_read_always_rechecks_disk_not_two_second_ram_mirror(self):
        FakeStore.documents['football_news_cache_abc'] = document()
        cold = Cold.FootballColdStartCache(object())
        first = await cold.async_entry_snapshot(entry(), force=True)
        self.assertEqual(first['fixtures'][0]['id'], 'match')
        new = document()
        new['datasets']['fixtures'][0]['id'] = 'new-durable-file'
        FakeStore.documents['football_news_cache_abc'] = new
        second = await cold.async_entry_snapshot(entry(), force=True)
        self.assertEqual(second['fixtures'][0]['id'], 'new-durable-file')

    async def test_partly_restored_registry_recovers_missing_competition(self):
        one, two = entry('abc', 'eng.1'), entry('second', 'esp.1')
        FakeStore.documents['football_news_cache_abc'] = document()
        FakeStore.documents['football_news_cache_second'] = document(league='esp.1')
        class Registry:
            async def fallback_entries(self):
                return [one, two]
        hass=SimpleNamespace(is_running=False, data={'football_news': {
            'entries': {}, 'cold_cache': Cold.FootballColdStartCache(object()),
            'league_registry': Registry()}},
            config_entries=SimpleNamespace(async_entries=lambda _domain: [one]))
        configured, saved, status = await async_store_first_snapshot(hass, [one])
        self.assertEqual({e.data['league'] for e in configured}, {'eng.1', 'esp.1'})
        self.assertTrue(status['registry_fallback'])
        self.assertEqual(status['store_restored'], 2)
        self.assertEqual(saved['second']['fixtures'][0]['id'], 'match')

    async def test_one_valid_and_one_recreated_entry_id_get_own_saved_files(self):
        active1, active2 = entry('abc', 'eng.1'), entry('new-id', 'esp.1')
        orphan2 = entry('old-id', 'esp.1')
        FakeStore.documents['football_news_cache_abc'] = document()
        # Fake recovery serves only validated data from a different entry ID.
        fallback = {'fixtures': [{'id':'saved-laliga'}], 'standings': [],
                    'news': [], 'updated_at': {'fixtures':'2026-11-25T00:00:00+00:00'}}
        class Recovery:
            async def async_snapshots(self):
                return [(orphan2, fallback)]
        hass = SimpleNamespace(is_running=True, data={'football_news': {
            'entries': {}, 'cold_cache': Cold.FootballColdStartCache(object()),
            'saved_cache_recovery': Recovery()}})
        configured, saved, status = await async_store_first_snapshot(hass, [active1, active2])
        self.assertEqual(status['store_restored'], 2)
        self.assertTrue(status['recovery_fallback'])
        self.assertEqual(saved['abc']['fixtures'][0]['id'], 'match')
        self.assertEqual(saved['new-id']['fixtures'][0]['id'], 'saved-laliga')

    async def test_slow_missing_cache_scan_does_not_hide_valid_saved_league(self):
        ready = asyncio.Event()
        events = []
        active1, active2 = entry('abc', 'eng.1'), entry('new-id', 'esp.1')
        FakeStore.documents['football_news_cache_abc'] = document()
        class Recovery:
            async def async_snapshots(self):
                await ready.wait()
                return [(entry('old-id', 'esp.1'), {
                    'fixtures':[{'id':'later-from-disk'}],
                    'updated_at':{'fixtures':'2026-11-27T00:00:00+00:00'}})]
        hass=SimpleNamespace(is_running=True, data={'football_news': {
            'entries':{}, 'cold_cache':Cold.FootballColdStartCache(object()),
            'saved_cache_recovery': Recovery()}},
            bus=SimpleNamespace(async_fire=lambda name, payload:events.append((name,payload))))
        _, saved, status = await async_store_first_snapshot(hass, [active1, active2])
        self.assertTrue(status['recovery_pending'])
        self.assertEqual(saved['abc']['fixtures'][0]['id'], 'match',
                         'valid HA Store feed cannot wait for a missing league scan')
        ready.set()
        await asyncio.wait_for(hass.data['football_news']['panel_missing_cache_scan_task'], 1)
        await asyncio.sleep(0)
        self.assertIn(('football_news_data_updated', {'phase':'saved_cache_scan_complete'}), events)
        _, recovered, status2 = await async_store_first_snapshot(hass, [active1, active2])
        self.assertEqual(recovered['new-id']['fixtures'][0]['id'], 'later-from-disk')
        self.assertEqual(status2['store_restored'],2)

    async def test_saved_feed_wins_over_stale_ram_but_newer_espn_wins(self):
        e = entry()
        saved = {'fixtures': [{'id':'ha-store'}],
                 'updated_at':{'fixtures':'2026-11-26T12:00:00+00:00'}}
        coordinator=SimpleNamespace(
            data={'fixtures':[{'id':'stale-ram'}],
                  'updated_at':{'fixtures':'2026-11-25T12:00:00+00:00'}},
            _last_errors=[], _attempted_refresh=True)
        runtime={'coordinator':coordinator, 'entry':e}
        rows=Snapshot.competition_snapshot([e], {'abc':runtime}, {'eng.1':'Premier League'}, {'abc':saved})
        self.assertEqual(rows[0]['fixtures'][0]['id'], 'ha-store')
        coordinator.data['updated_at']['fixtures']='2026-11-27T12:00:00+00:00'
        rows=Snapshot.competition_snapshot([e], {'abc':runtime}, {'eng.1':'Premier League'}, {'abc':saved})
        self.assertEqual(rows[0]['fixtures'][0]['id'], 'stale-ram')


if __name__ == '__main__':
    unittest.main()
