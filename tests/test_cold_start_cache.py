"""Cold sidebar read: backend can show disk data before config entry runtime exists."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from test_disk_cache import FakeStore, load_modules

BASE = Path(__file__).resolve().parents[1] / "custom_components" / "football_news"
DiskCache, _ = load_modules()
PKG = "_football_news_disk_test"
package = types.ModuleType(PKG)
package.__path__ = [str(BASE)]
sys.modules[PKG] = package
sys.modules[PKG + ".disk_cache"] = DiskCache
for module_name in ("const", "qualification", "snapshot", "cold_start"):
    full_name = PKG + "." + module_name
    spec = importlib.util.spec_from_file_location(full_name, BASE / (module_name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[full_name] = module
    spec.loader.exec_module(module)
Snapshot = sys.modules[PKG + ".snapshot"]
Cold = sys.modules[PKG + ".cold_start"]


def entry(entry_id="abc", league="eng.1"):
    return SimpleNamespace(entry_id=entry_id, data={"league": league},
                           runtime_data=None, state="setup_in_progress", options={})


def document(league="eng.1", season=2026):
    now = datetime.now(timezone.utc).isoformat()
    return {"schema": 1, "league": league, "season": season,
            "datasets": {"fixtures": [{"id": "match", "state": "pre", "kickoff": now}],
                         "standings": [{"position": 1, "name": "Arsenal", "points": 30}]},
            "updated_at": {"fixtures": now, "standings": now}}


class ColdStartCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.documents.clear()
        FakeStore.writes.clear()
        self.hass = object()

    async def test_first_sidebar_returns_persisted_data_before_coordinator_exists(self):
        FakeStore.documents["football_news_cache_abc"] = document()
        e = entry()
        index = Cold.FootballColdStartCache(self.hass)
        fallback = await index.async_entry_snapshot(e)
        self.assertEqual(fallback["fixtures"][0]["id"], "match")
        rows = Snapshot.competition_snapshot([e], {}, {"eng.1": "Premier League"},
                                             {e.entry_id: fallback})
        self.assertEqual(len(rows), 1)
        self.assertFalse(rows[0]["runtime_loaded"])
        self.assertTrue(rows[0]["ready"], "cache data must be shown despite unloaded runtime")
        self.assertEqual(rows[0]["standings"][0]["name"], "Arsenal")
        self.assertEqual(rows[0]["cache_info"]["restored_datasets"], ["fixtures", "standings"])

    async def test_stale_or_wrong_season_cache_not_displayed(self):
        FakeStore.documents["football_news_cache_abc"] = document(season=2025)
        self.assertFalse(await Cold.FootballColdStartCache(self.hass).async_entry_snapshot(entry()))
        FakeStore.documents["football_news_cache_abc"] = document(league="esp.1")
        self.assertFalse(await Cold.FootballColdStartCache(self.hass).async_entry_snapshot(entry()))

    async def test_preload_does_not_overwrite_new_coordinator_rows(self):
        e = entry()
        old = document()
        cache_data = {"fixtures": old["datasets"]["fixtures"],
                      "standings": old["datasets"]["standings"],
                      "updated_at": old["updated_at"], "cache_info": {"restored_datasets": ["fixtures", "standings"]}}
        coordinator = SimpleNamespace(
            data={"fixtures": [{"id": "new", "state": "post"}],
                  "updated_at": {"fixtures": datetime.now(timezone.utc).isoformat()}},
            _last_errors=[], _attempted_refresh=True,
        )
        runtime = {"coordinator": coordinator}
        e.runtime_data = runtime
        rows = Snapshot.competition_snapshot([e], {"abc": runtime},
                    {"eng.1": "Premier League"}, {"abc": cache_data})
        self.assertEqual(rows[0]["fixtures"][0]["id"], "new", "new ESPN wins over old disk")
        self.assertEqual(rows[0]["standings"][0]["name"], "Arsenal", "missing feed uses disk")
        self.assertTrue(rows[0]["ready"])

    async def test_concurrent_read_deduplicated_with_lock(self):
        FakeStore.documents["football_news_cache_abc"] = document()
        index = Cold.FootballColdStartCache(self.hass)
        snapshots = await asyncio.gather(*[index.async_entry_snapshot(entry()) for _ in range(8)])
        self.assertTrue(all(s == snapshots[0] for s in snapshots))
        self.assertEqual(len(index._loaded), 1)

    async def test_old_live_score_not_marked_live_in_cold_cache(self):
        doc=document()
        doc["datasets"]["fixtures"][0]["state"]="in"
        FakeStore.documents["football_news_cache_abc"] = doc
        cached=await Cold.FootballColdStartCache(self.hass).async_entry_snapshot(entry())
        self.assertEqual(cached["fixtures"][0]["state"], "unknown")

if __name__ == "__main__":
    unittest.main()

# Verify the production WebSocket handler rather than just its helper functions.
import ast
import logging


def bare_websocket_data_handler():
    tree = ast.parse((BASE / "__init__.py").read_text(encoding="utf-8"))
    node = next(item for item in tree.body if isinstance(item, ast.AsyncFunctionDef)
                and item.name == "ws_get_data")
    node.decorator_list = []
    script = ast.Module(body=[node], type_ignores=[])
    globals_dict = {"asyncio": asyncio, "DOMAIN": "football_news",
                    "LEAGUES": {"eng.1": "Premier League"}, "STARTER_LEAGUES": ("eng.1",),
                    "runtime_for_entry": Snapshot.runtime_for_entry,
                    "competition_snapshot": Snapshot.competition_snapshot,
                    "_LOGGER": logging.getLogger("test"),
                    "_runtime": lambda _hass, _id="": None}
    exec(compile(ast.fix_missing_locations(script), str(BASE / "__init__.py"), "exec"), globals_dict)
    return globals_dict["ws_get_data"]


class WebSocketColdEntryTests(unittest.IsolatedAsyncioTestCase):
    async def test_production_ws_returns_disk_fixture_without_runtime(self):
        FakeStore.documents.clear()
        FakeStore.documents["football_news_cache_abc"] = document()
        cold_index = Cold.FootballColdStartCache(object())
        entries = [entry()]
        class Prefs:
            async def read(self): return {"clubs": [], "matches": [], "leagues": []}
        class Entries:
            def async_entries(self, domain):
                assert domain == "football_news"
                return entries
        class Connection:
            user = SimpleNamespace(is_admin=True)
            def send_result(self, id, data): self.sent = data
        hass = SimpleNamespace(config_entries=Entries(), data={"football_news": {
            "entries": {}, "cold_cache": cold_index, "preferences": Prefs()}})
        conn = Connection()
        await bare_websocket_data_handler()(hass, conn, {"id": 9})
        self.assertEqual(conn.sent["configured_count"], 1)
        self.assertEqual(conn.sent["runtime_count"], 0)
        self.assertEqual(conn.sent["leagues"][0]["fixtures"][0]["id"], "match")
        self.assertEqual(conn.sent["leagues"][0]["cache_info"]["type"], "disk")
        self.assertTrue(conn.sent["leagues"][0]["ready"])

    async def test_cold_restore_failure_does_not_crash_other_league(self):
        FakeStore.documents.clear()
        FakeStore.documents["football_news_cache_good"] = document()
        entries = [entry("good"), entry("bad", "esp.1")]
        cold = Cold.FootballColdStartCache(object())
        class Prefs:
            async def read(self): return {"clubs": [], "matches": []}
        class Entries:
            def async_entries(self, _): return entries
        class Connection:
            user = None
            def send_result(self, _, value): self.sent=value
        hass=SimpleNamespace(config_entries=Entries(),data={"football_news":{
            "entries": {},"cold_cache": cold,"preferences":Prefs()}})
        conn=Connection()
        await bare_websocket_data_handler()(hass,conn,{"id":3})
        self.assertEqual(len(conn.sent["leagues"]),2)
        self.assertTrue(conn.sent["leagues"][0]["ready"])
        self.assertFalse(conn.sent["leagues"][1]["ready"])
