"""Explicit HA Store refresh creates a new server task when an old read hangs."""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from test_cold_start_cache import bare_websocket_data_handler, entry


class ForceStoreWebSocketTests(unittest.IsolatedAsyncioTestCase):
    async def test_manual_force_skips_old_unresolved_store_task(self):
        first_read = asyncio.Event()
        calls = 0
        ent = entry()
        class Config:
            def async_entries(self, _):
                return [ent]
        class Conn:
            user = SimpleNamespace(id='ha-user', is_admin=True)
            def send_result(self, _id, payload):
                self.payload = payload
        def data(fixture_id):
            return ([ent], {'abc': {'fixtures': [{'id':fixture_id}],
                'updated_at': {'fixtures':'2026-11-27T00:00:00+00:00'}}},
                {'store_attempted':1,'store_restored':1,'store_errors':0,
                 'registry_fallback':False,'recovery_fallback':False})
        async def store(_hass, _entries):
            nonlocal calls
            calls += 1
            if calls == 1:
                await first_read.wait()
                return data('old-store')
            return data('fresh-store')
        ws = bare_websocket_data_handler()
        ws.__globals__['async_store_first_snapshot'] = store
        hass=SimpleNamespace(is_running=True, config_entries=Config(),
                             data={'football_news':{'entries':{}}})
        old = Conn()
        first = asyncio.create_task(ws(hass, old, {'id':1, 'fast':True}))
        await asyncio.sleep(0)
        new = Conn()
        await asyncio.wait_for(ws(hass, new,
            {'id':2,'fast':True,'store_refresh':True}), 0.4)
        self.assertEqual(calls, 2)
        self.assertEqual(new.payload['leagues'][0]['fixtures'][0]['id'], 'fresh-store')
        first_read.set()
        await asyncio.wait_for(first, 0.4)


if __name__ == '__main__':
    unittest.main()
