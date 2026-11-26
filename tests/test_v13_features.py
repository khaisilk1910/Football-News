"""V13 soccer source classification and Zalo team ID filtering tests."""
import asyncio
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_provider_fallback import models
from test_notifications import notice, FakeServices, MemoryStore
from test_snapshot import module as snapshot_module, entry as make_entry
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace


class LeagueZoneTests(unittest.TestCase):
    def test_epl_20_team_zones(self):
        rows = [{"id": str(i), "position": i, "name": f"Team {i}"} for i in range(1, 21)]
        coord = SimpleNamespace(data={"standings": rows, "updated_at": {"standings": "now"}},
                                _last_errors=[], _attempted_refresh=True)
        entries=[make_entry("e1", "eng.1", runtime={"coordinator": coord})]
        result=snapshot_module.competition_snapshot(entries, {}, {"eng.1": "Premier League"})[0]
        zones=[item["zone"] for item in result["standings"]]
        self.assertEqual(zones[0], "champion")
        self.assertEqual(zones[3], "champions")
        self.assertEqual(zones[4], "")  # fifth C1 spot is NOT guaranteed for next season
        self.assertEqual(zones[-3:], ["relegation"] * 3)

    def test_bundesliga_and_missing_table(self):
        from test_snapshot import sys as _sys
        module = _sys.modules["football_news_snapshot_test.qualification"]
        self.assertEqual(module.position_zone("ger.1", 16, 18), "playoff")
        self.assertEqual(module.position_zone("ger.1", 17, 18), "relegation")
        self.assertEqual(module.position_zone("fra.1", 3, 18), "champions")
        self.assertEqual(module.position_zone("eng.1", 18, 19), "")
        self.assertEqual(module.position_zone("uefa.champions", 1, 36), "")

    def test_nested_goal_stats_without_guessing_other_values(self):
        sample={"athletes": [{"athlete": {"id":"17", "displayName":"Cầu thủ A"},
                "team":{"name":"CLB A"}, "splits":{"categories": [{"name":"general",
                "stats":[{"name":"goals","value":15}, {"name":"fouls","value":99}]}]}}]}
        rows=models.normalize_leaders(sample)
        self.assertEqual(len(rows),1)
        self.assertEqual((rows[0]["category"],rows[0]["value"]),("goals",15))

    def test_round_is_from_provider_metadata_only(self):
        base={"id":"12","date":"2026-11-21T12:00:00Z", "competitions":[{"round":{"number":7},
             "competitors":[{"homeAway":"home","team":{"id":"1","name":"A"}},
                           {"homeAway":"away","team":{"id":"2","name":"B"}}]}]}
        self.assertEqual(models.normalize_fixture(base,"eng.1")["round"],7)
        base["competitions"][0].pop("round")
        self.assertIsNone(models.normalize_fixture(base,"eng.1")["round"])


class ZaloSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        MemoryStore.values.clear()
        self.hass=SimpleNamespace(services=FakeServices(), config=SimpleNamespace(time_zone="Asia/Ho_Chi_Minh"))
        self.entry=SimpleNamespace(entry_id="v13",data={"league":"eng.1"},options={
            "zalo_enabled":True,"zalo_account":"acct","zalo_thread_id":"12345678901234567",
            "zalo_team_ids":["17","19"],"zalo_team_names":["Arsenal", "Chelsea"],
            "schedule_alerts":True,"news_alerts":True})
        self.notifier=notice.ZaloNotifier(self.hass,self.entry,"Premier League")

    def fixture(self, home_id, away_id):
        return {"id": f"{home_id}{away_id}", "state":"pre",
                "kickoff":(datetime.now(timezone.utc)+timedelta(minutes=10)).isoformat(),
                "home":{"id":home_id,"name":"Arsenal" if home_id=="17" else "Elsewhere"},
                "away":{"id":away_id,"name":"Chelsea" if away_id=="19" else "Elsewhere"}}

    async def test_selected_teams_receive_notifications_only(self):
        await self.notifier.process({"fixtures":[self.fixture("20","21"),self.fixture("17","31"),
                                                  self.fixture("40","19")],"news":[]})
        self.assertEqual(len(self.hass.services.calls),2)
        self.assertTrue(all("Elsewhere" in call["message"] for call in self.hass.services.calls))

    async def test_absent_ids_dont_accidentally_match_names(self):
        unlisted=self.fixture("89","90")
        unlisted["home"]["name"]="Arsenal"
        await self.notifier.process({"fixtures":[unlisted],"news":[]})
        self.assertEqual(len(self.hass.services.calls),0)

if __name__=="__main__":unittest.main()
