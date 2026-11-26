"""Cold HA Store must not strand the first WebSocket or require navigation."""
from __future__ import annotations

import asyncio
import types
import unittest
from types import SimpleNamespace

from test_cold_start_cache import bare_websocket_data_handler, document, entry


class StoreFirstDeadlineTests(unittest.IsolatedAsyncioTestCase):
    async def test_background_store_completion_wakes_connected_panels(self):
        signal = asyncio.Event()
        events = []
        class Config:
            def async_entries(self, domain):
                assert domain == 'football_news'
                return [entry()]
        class Conn:
            user = SimpleNamespace(id='user', is_admin=True)
            def send_result(self, _id, result):
                self.result = result
        async def delayed(_hass, configured):
            await signal.wait()
            stored = document()
            return configured, {
                'abc': {'fixtures': stored['datasets']['fixtures'],
                        'standings': stored['datasets']['standings'],
                        'updated_at': stored['updated_at'],
                        'cache_info': {'restored_datasets': ['fixtures', 'standings']}}
            }, {'store_attempted':1,'store_restored':1,'store_errors':0,
                'registry_fallback':False,'recovery_fallback':False}
        async def instant_deadline(awaitable, timeout):
            if timeout == 6:
                await asyncio.sleep(0)
                raise asyncio.TimeoutError
            return await asyncio.wait_for(awaitable, timeout)
        ws = bare_websocket_data_handler()
        ws.__globals__['async_store_first_snapshot'] = delayed
        ws.__globals__['asyncio'] = types.SimpleNamespace(
            create_task=asyncio.create_task, shield=asyncio.shield,
            wait_for=instant_deadline, TimeoutError=asyncio.TimeoutError)
        hass = SimpleNamespace(is_running=True,
            config_entries=Config(), data={'football_news': {'entries': {}}},
            bus=SimpleNamespace(async_fire=lambda event, payload: events.append((event,payload))))
        first = Conn()
        await ws(hass, first, {'id':1, 'fast':True})
        self.assertTrue(first.result['recovery_status']['store_pending'])
        self.assertEqual(first.result['leagues'][0]['fixtures'], [])
        self.assertIn('backend_version', first.result)
        signal.set()
        await asyncio.wait_for(hass.data['football_news']['panel_store_first_read_task'], 0.5)
        await asyncio.sleep(0)
        self.assertIn(('football_news_data_updated',{'phase':'store_read_complete'}), events)
        # The next read must return the authoritative Store snapshot, without
        # leaving the panel and reentering the sidebar.
        ws.__globals__['asyncio'] = asyncio
        second = Conn()
        await ws(hass, second, {'id':2, 'fast':True})
        self.assertEqual(second.result['leagues'][0]['fixtures'][0]['id'], 'match')
        self.assertEqual(second.result['cache_source'], 'ha_store')


if __name__ == '__main__':
    unittest.main()
