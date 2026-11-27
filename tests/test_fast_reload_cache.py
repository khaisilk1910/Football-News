"""Regression: browser reload always checks shared HA Store, preserving fresher RAM feeds."""
import asyncio
import unittest
from types import SimpleNamespace

from test_cold_start_cache import bare_websocket_data_handler, entry


class CacheReloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_websocket_reads_store_on_each_reload_even_when_runtime_is_loaded(self):
        ent = entry()
        ent.options = {'locale': 'vi'}
        class Entries:
            def async_entries(self, domain):
                return [ent]
        class Coordinator:
            _cache_loaded = True
            _last_errors = []
            _attempted_refresh = True
            data = {
                'fixtures': [{'id':'live-101','state':'pre','home':{'name':'Arsenal'},'away':{'name':'Chelsea'}}],
                'standings': [{'name':'Arsenal','position':1,'points':23}],
                'news': [], 'updated_at': {'fixtures':'2026-11-20T04:00:01+00:00', 'standings':'2026-11-20T04:00:01+00:00'},
            }
            async def async_restore_cache(self):
                raise AssertionError('must not re-open HA Store on browser reload')
        class Cold:
            reads = 0
            async def async_entry_snapshot(self, _entry, *, force=False):
                self.reads += 1
                assert force, 'HA Store-first read must bypass long-lived RAM mirror'
                return {'fixtures':[{'id':'saved-101','state':'pre'}],
                        'standings':[{'name':'Saved Arsenal','position':1,'points':20}],
                        'updated_at':{'fixtures':'2026-11-20T04:00:00+00:00',
                                      'standings':'2026-11-20T04:00:00+00:00'},
                        'cache_info':{'type':'disk','restored_datasets':['fixtures','standings']}}
        class Prefs:
            async def read(self): return {'clubs':[], 'matches':[], 'leagues':[]}
        class Conn:
            user = SimpleNamespace(id='test', is_admin=True)
            def send_result(self, _id, result): self.result=result
        coordinator=Coordinator()
        cold = Cold()
        runtime={'entry':ent,'coordinator':coordinator}
        hass=SimpleNamespace(is_running=True,config_entries=Entries(),data={'football_news':{
            'entries':{'abc':runtime},'cold_cache':cold,'preferences':Prefs(),
        }})
        for _ in range(2):
            c=Conn()
            await bare_websocket_data_handler()(hass,c,{'id':1})
            self.assertEqual(c.result['leagues'][0]['fixtures'][0]['id'],'live-101')
            self.assertEqual(c.result['leagues'][0]['standings'][0]['name'],'Arsenal')
        self.assertEqual(cold.reads, 2, 'every independent WebSocket read checks HA Store')

if __name__ == '__main__': unittest.main()
