"""Test the actual nonblocking HA Store prewarming helper, with HA stubs."""
import ast
import asyncio
import logging
import unittest
from pathlib import Path
from types import SimpleNamespace

from test_cold_start_cache import Cold, FakeStore, Snapshot, document, entry

ROOT = Path(__file__).resolve().parents[1]/'custom_components'/'football_news'

def warm_helper():
    tree = ast.parse((ROOT/'__init__.py').read_text())
    fn = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name=='_start_panel_cache_warm')
    module = ast.Module(body=[fn],type_ignores=[])
    ns = {'HomeAssistant':object,'asyncio':asyncio,'monotonic':__import__('time').monotonic,
          'DOMAIN':'football_news','_LOGGER':logging.getLogger('test'),
          'runtime_for_entry': Snapshot.runtime_for_entry}
    exec(compile(ast.fix_missing_locations(module),str(ROOT/'__init__.py'),'exec'),ns)
    return ns['_start_panel_cache_warm']

class WarmHelperTests(unittest.IsolatedAsyncioTestCase):
    async def test_first_response_never_waits_for_disk_and_task_is_shared(self):
        FakeStore.documents.clear()
        FakeStore.documents['football_news_cache_abc']=document()
        ent = entry()
        reader=Cold.FootballColdStartCache(object())
        original=reader.async_entry_snapshot
        gate=asyncio.Event()
        calls=0
        async def slow(ent):
            nonlocal calls
            calls+=1
            await gate.wait()
            return await original(ent)
        reader.async_entry_snapshot=slow
        signals=[]
        state={'entries':{},'cold_cache':reader}
        hass=SimpleNamespace(data={'football_news':state},
            async_create_task=lambda coro:asyncio.create_task(coro),
            bus=SimpleNamespace(async_fire=lambda *args:signals.append(args)))
        warm=warm_helper()
        warm(hass,[ent]);warm(hass,[ent]);await asyncio.sleep(0);await asyncio.sleep(0)
        self.assertEqual(calls,1,'two simultaneous panels share one disk read')
        self.assertFalse(state['panel_cache_warm_task'].done())
        gate.set()
        await asyncio.wait_for(state['panel_cache_warm_task'],timeout=0.5)
        self.assertEqual(state['panel_cache_warm_snapshots']['abc']['fixtures'][0]['id'],'match')
        self.assertTrue(signals,'HA broadcasts local cache readiness to connected panels')

if __name__=='__main__':unittest.main()
