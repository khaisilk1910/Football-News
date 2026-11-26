"""Regression: every new device consumes the same validated HA Store file."""
from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from test_cold_start_cache import Cold, FakeStore, bare_websocket_data_handler, document, entry


class StoreFirstMultiDeviceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.documents.clear()
        FakeStore.writes.clear()

    def hass_for(self, entries, cold):
        class Entries:
            def async_entries(self, domain):
                assert domain == "football_news"
                return entries
        return SimpleNamespace(is_running=True, config_entries=Entries(), data={
            "football_news": {"entries": {}, "cold_cache": cold}})

    @staticmethod
    def conn():
        class Conn:
            user = SimpleNamespace(id="same_user", is_admin=False)
            def send_result(self, _id, response): self.result = response
        return Conn()

    async def test_two_devices_get_saved_leagues_with_empty_ram(self):
        FakeStore.documents["football_news_cache_abc"] = document()
        saved = entry()
        cold = Cold.FootballColdStartCache(object())
        hass = self.hass_for([saved], cold)
        first, second = self.conn(), self.conn()
        await asyncio.gather(
            bare_websocket_data_handler()(hass, first, {"id": 1, "fast": True}),
            bare_websocket_data_handler()(hass, second, {"id": 2, "fast": True}),
        )
        for conn in [first, second]:
            self.assertEqual(conn.result["leagues"][0]["fixtures"][0]["id"], "match")
            self.assertEqual(conn.result["leagues"][0]["standings"][0]["name"], "Arsenal")
            self.assertEqual(conn.result["cache_source"], "ha_store")
            self.assertEqual(conn.result["recovery_status"]["store_restored"], 1)

    async def test_reload_reads_new_durable_snapshot_not_old_mirror(self):
        stored = document()
        FakeStore.documents["football_news_cache_abc"] = stored
        cold = Cold.FootballColdStartCache(object())
        hass = self.hass_for([entry()], cold)
        one = self.conn()
        await bare_websocket_data_handler()(hass, one, {"id": 1, "fast": True})
        self.assertEqual(one.result["leagues"][0]["fixtures"][0]["id"], "match")
        newer = document()
        newer["datasets"]["fixtures"][0]["id"] = "match-new"
        FakeStore.documents["football_news_cache_abc"] = newer
        # The short cross-device single-flight window is over.
        for key, (_, snapshot) in list(cold._loaded.items()):
            cold._loaded[key] = (0, snapshot)
        two = self.conn()
        await bare_websocket_data_handler()(hass, two, {"id": 2, "fast": True})
        self.assertEqual(two.result["leagues"][0]["fixtures"][0]["id"], "match-new")
        self.assertEqual(two.result["cache_source"], "ha_store")

    async def test_corrupted_store_uses_current_server_coordinator_and_logs_status(self):
        ent = entry()
        FakeStore.documents["football_news_cache_abc"] = {"schema": 9, "league": "eng.1"}
        coordinator = SimpleNamespace(
            data={"fixtures": [{"id": "ram-current", "state": "pre"}],
                  "updated_at": {"fixtures": "2026-11-26T00:00:00+00:00"}},
            _last_errors=[], _attempted_refresh=True)
        ent.runtime_data = {"entry": ent, "coordinator": coordinator}
        hass = self.hass_for([ent], Cold.FootballColdStartCache(object()))
        hass.data["football_news"]["entries"][ent.entry_id] = ent.runtime_data
        conn = self.conn()
        await bare_websocket_data_handler()(hass, conn, {"id": 2, "fast": True})
        self.assertEqual(conn.result["leagues"][0]["fixtures"][0]["id"], "ram-current")
        self.assertEqual(conn.result["cache_source"], "memory")
        self.assertEqual(conn.result["recovery_status"]["store_restored"], 0)

    async def test_unconfigured_install_reports_missing_store_not_invented_fixtures(self):
        cold = Cold.FootballColdStartCache(object())
        hass = self.hass_for([entry()], cold)
        conn = self.conn()
        await bare_websocket_data_handler()(hass, conn, {"id": 1, "fast": True})
        self.assertEqual(conn.result["leagues"][0]["fixtures"], [])
        self.assertEqual(conn.result["cache_source"], "none")
        self.assertEqual(conn.result["recovery_status"]["store_attempted"], 1)

    async def test_snapshot_from_one_league_never_leaks_into_another(self):
        FakeStore.documents["football_news_cache_one"] = document(league="eng.1")
        FakeStore.documents["football_news_cache_two"] = document(league="eng.1")
        cold = Cold.FootballColdStartCache(object())
        hass = self.hass_for([entry("one", "eng.1"), entry("two", "esp.1")], cold)
        conn = self.conn()
        await bare_websocket_data_handler()(hass, conn, {"id": 1, "fast": True})
        by_code = {row["league_code"]: row for row in conn.result["leagues"]}
        self.assertEqual(by_code["eng.1"]["fixtures"][0]["id"], "match")
        self.assertEqual(by_code["esp.1"]["fixtures"], [])


if __name__ == "__main__": unittest.main()
