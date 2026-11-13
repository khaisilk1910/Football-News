"""Cache regression tests: disk rehydration, stale safety, partial outage, scope.

Home Assistant Store and coordinator are stubbed so these tests do not require
Home Assistant installed; they do NOT pretend to test a live ESPN response.
"""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "football_news"
PKG = "_football_news_disk_test"

class FakeStore:
    documents = {}
    writes = []
    def __init__(self, hass, version, key):
        self.key = key
    async def async_load(self):
        return self.documents.get(self.key)
    def async_delay_save(self, factory, delay):
        self.documents[self.key] = factory()
        self.writes.append((self.key, delay))

class FakeBase:
    def __class_getitem__(cls, _item):
        return cls
    def __init__(self, hass, logger, **kwargs):
        self.hass = hass
        self.data = None
        self.update_interval = kwargs.get("update_interval")
    def async_set_updated_data(self, data):
        self.data = data

class FakeError(Exception):
    pass

def fake_module(name):
    return types.ModuleType(name)

def load_modules():
    names = {name: fake_module(name) for name in (
        "homeassistant", "homeassistant.helpers", "homeassistant.helpers.storage",
        "homeassistant.helpers.update_coordinator")}
    names["homeassistant.helpers.storage"].Store = FakeStore
    names["homeassistant.helpers.update_coordinator"].DataUpdateCoordinator = FakeBase
    names["homeassistant.helpers.update_coordinator"].UpdateFailed = FakeError
    with patch.dict(sys.modules, names):
        package = types.ModuleType(PKG)
        package.__path__ = [str(COMPONENT)]
        sys.modules[PKG] = package
        mock_provider = types.ModuleType(PKG + ".provider")
        mock_provider.FootballProvider = object
        mock_provider.ProviderError = FakeError
        sys.modules[mock_provider.__name__] = mock_provider
        for filename in ("const", "disk_cache", "coordinator"):
            spec = importlib.util.spec_from_file_location(
                PKG + "." + filename, COMPONENT / (filename + ".py"))
            obj = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = obj
            spec.loader.exec_module(obj)
        return sys.modules[PKG + ".disk_cache"], sys.modules[PKG + ".coordinator"]

cache, coordinator_module = load_modules()

class MockProvider:
    league = "eng.1"
    def _season_year(self):
        return 2026
    def __init__(self):
        self.fail = False
        self.calls = 0
    async def fixtures(self):
        self.calls += 1
        if self.fail: raise FakeError("offline")
        return [{"id": "f1", "state": "pre", "kickoff": "2026-11-21T12:00:00Z"}]
    async def standings(self):
        if self.fail: raise FakeError("offline")
        return [{"id": "t1", "name": "Arsenal", "points": 21}]
    async def news(self):
        if self.fail: raise FakeError("offline")
        return []
    async def leaders(self):
        if self.fail: raise FakeError("offline")
        return [{"player": "Example", "team": "Arsenal", "value": 10,
                 "category": "goals", "photo": "https://test.invalid/a.png"}]

class DiskCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.documents.clear()
        FakeStore.writes.clear()
        self.now = datetime.now(timezone.utc)
        self.hass = types.SimpleNamespace(async_create_task=lambda coroutine: asyncio.create_task(coroutine))
    def instance(self, entry_id="first", provider=None):
        entry = types.SimpleNamespace(entry_id=entry_id)
        provider = provider or MockProvider()
        return coordinator_module.FootballNewsCoordinator(self.hass, entry, provider)

    async def test_cache_keeps_public_data_without_network_during_init(self):
        c = self.instance()
        self.assertIsNone(c.data)
        self.assertEqual(c.provider.calls, 0)
        self.assertEqual(FakeStore.writes, [])
        fresh = await c._async_update_data()
        self.assertEqual(len(fresh["fixtures"]), 1)
        self.assertTrue(FakeStore.documents)
        assert "football_news_cache_first" in FakeStore.documents
        restarted_provider = MockProvider()
        restored = self.instance(provider=restarted_provider)
        await restored.async_restore_cache()
        self.assertEqual(restarted_provider.calls, 0, "disk load never calls ESPN")
        self.assertEqual(restored.data["standings"][0]["name"], "Arsenal")
        self.assertEqual(restored.data["cache_info"]["restored_datasets"],
                         ["fixtures", "news", "standings"])
        self.assertFalse(restored._attempted_refresh)

    async def test_cache_restore_live_match_never_claims_live(self):
        key = "football_news_cache_first"
        FakeStore.documents[key] = {"schema": 1, "league": "eng.1", "season": 2026,
            "datasets": {"fixtures": [{"id": "1", "state": "in", "status": "Live"}]},
            "updated_at": {"fixtures": self.now.isoformat()}}
        restored = self.instance()
        await restored.async_restore_cache()
        self.assertEqual(restored.data["fixtures"][0]["state"], "unknown")
        self.assertIn("fixtures", restored.data["cache_info"]["restored_datasets"])
        live = await restored._async_update_data()
        self.assertEqual(live["cache_info"]["restored_datasets"], [])
        self.assertEqual(live["fixtures"][0]["state"], "pre")

    async def test_partial_failure_keeps_disk_standings_and_marks_stale(self):
        key = "football_news_cache_first"
        FakeStore.documents[key] = {"schema":1,"league":"eng.1","season":2026,
            "datasets":{"standings":[{"name":"Last-known good", "points":19}]},
            "updated_at":{"standings":self.now.isoformat()}}
        obj = self.instance(provider=MockProvider())
        obj.provider.fail = True
        await obj.async_restore_cache()
        result = await obj._async_update_data()
        self.assertEqual(result["standings"][0]["name"], "Last-known good")
        self.assertIn("standings", result["cache_info"]["restored_datasets"])
        self.assertEqual(len(result["errors"]),3)

    async def test_stale_future_wrong_league_and_corrupt_cache_are_rejected(self):
        doc={"schema":1,"league":"esp.1", "datasets":{"news":[{"id":"n"}]},
             "updated_at":{"news":self.now.isoformat()}}
        self.assertEqual(cache.validated_snapshot(doc,"eng.1")["datasets"],{})
        doc["league"]="eng.1"
        doc["season"]=2025
        self.assertEqual(cache.validated_snapshot(doc,"eng.1",season=2026)["datasets"],{})
        doc["season"]=2026
        doc["updated_at"]["news"]=(self.now-timedelta(days=5)).isoformat()
        self.assertEqual(cache.validated_snapshot(doc,"eng.1")["datasets"],{})
        doc["updated_at"]["news"]=(self.now+timedelta(days=1)).isoformat()
        self.assertEqual(cache.validated_snapshot(doc,"eng.1")["datasets"],{})
        self.assertEqual(cache.validated_snapshot({"schema":1,"league":"eng.1","season":2026, "datasets": []},"eng.1")["datasets"],{})

    async def test_leaders_saved_without_images_and_restored_for_next_session(self):
        obj = self.instance()
        players,cached = await obj.async_leaders()
        self.assertFalse(cached)
        self.assertEqual(players[0]["player"], "Example")
        doc = FakeStore.documents["football_news_cache_first"]
        self.assertNotIn("photo", doc["datasets"]["leaders"][0])
        new = self.instance()
        await new.async_restore_cache()
        self.assertEqual(new.provider.calls,0)
        players,cached=await new.async_leaders()
        self.assertTrue(cached)
        self.assertEqual(players[0]["player"],"Example")

    async def test_first_empty_response_preserves_good_then_second_confirms_empty(self):
        obj = self.instance()
        good = await obj._async_update_data()
        self.assertEqual(len(good["standings"]), 1)
        async def empty(): return []
        obj.provider.standings = empty
        first = await obj._async_update_data()
        self.assertEqual(len(first["standings"]), 1)
        self.assertTrue(any("empty ESPN response" in value for value in first["errors"]))
        second = await obj._async_update_data()
        self.assertEqual(second["standings"], [])
        self.assertFalse(any("empty ESPN response" in value for value in second["errors"]))

    async def test_zalo_only_sees_fresh_espn_feeds_on_partial_outage(self):
        obj = self.instance()
        messages=[]
        class Notifier:
            async def process(self, data): messages.append(data)
        obj.notifier = Notifier()
        # A restored score and news article must never be re-sent on a failed
        # endpoint while another feed succeeds.
        obj._data["fixtures"]=[{"id":"historic", "state":"post"}]
        obj._dataset_updates["fixtures"]=self.now
        obj._restored_datasets.add("fixtures")
        obj._data["news"]=[{"id":"historic-news"}]
        obj._dataset_updates["news"]=self.now
        obj._restored_datasets.add("news")
        async def failure(): raise FakeError("HTTP 429")
        obj.provider.fixtures=failure
        obj.provider.news=failure
        await obj._async_update_data()
        self.assertEqual(len(messages),0)
        async def news(): return [{"id":"fresh"}]
        obj.provider.news=news
        await obj._async_update_data()
        await asyncio.sleep(0)
        self.assertEqual(len(messages),1)
        self.assertEqual(messages[0]["fixtures"],[])
        self.assertEqual(messages[0]["news"],[{"id":"fresh"}])

    async def test_empty_leaders_response_never_erases_prior_good_leaders(self):
        obj = self.instance()
        rows, _ = await obj.async_leaders()
        self.assertEqual(len(rows), 1)
        obj._leader_updated = self.now - timedelta(hours=7)
        async def empty(): return []
        obj.provider.leaders = empty
        rows, from_cache = await obj.async_leaders()
        self.assertTrue(from_cache)
        self.assertEqual(rows[0]["player"], "Example")

    async def test_independent_league_entry_files_and_single_disk_read(self):
        a=self.instance("one")
        b=self.instance("two")
        await asyncio.gather(a.async_restore_cache(), a.async_restore_cache(), b.async_restore_cache())
        a._dataset_updates["news"] = self.now
        a._data["news"] = [{"id":"1"}]
        a._persist(force=True)
        self.assertIn("football_news_cache_one",FakeStore.documents)
        self.assertNotIn("football_news_cache_two",FakeStore.documents)
        self.assertEqual((await b._disk.load())["datasets"],{})

if __name__ == "__main__": unittest.main()
