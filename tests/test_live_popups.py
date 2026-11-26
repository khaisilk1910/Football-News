"""Backend regression tests for verified all-league Live events and dedup."""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest

from test_disk_cache import coordinator_module, MockProvider, FakeStore
from _football_news_disk_test.live_events import LiveEventTracker, extract_events, event_kind, fixture_score_from_summary


def fixture(score=1):
    return {
        "id": "401900111", "league": "eng.1", "state": "in",
        "kickoff": datetime.now(timezone.utc).isoformat(),
        "home": {"id": "1", "name": "Arsenal", "logo": "https://a.espncdn.com/a.png", "score": score},
        "away": {"id": "2", "name": "Chelsea", "logo": "https://a.espncdn.com/b.png", "score": 0},
    }


def goal(identifier="g1"):
    return {"id": identifier, "type": {"text": "Goal"}, "clock": {"displayValue": "52'"},
            "team": {"id": "1", "displayName": "Arsenal"},
            "participants": [{"athlete": {"displayName": "Bukayo Saka"}}],
            "text": "Goal from open play"}


def yellow(identifier="y1"):
    return {"id": identifier, "type": {"text": "Yellow Card"},
            "clock": {"displayValue": "63'"}, "team": {"id": "2"},
            "participants": [{"athlete": {"displayName": "Reece James"}}]}


def red(identifier="r1"):
    return {"id": identifier, "type": {"text": "Second Yellow Card"},
            "clock": {"displayValue": "78'"}, "team": {"id": "2"},
            "participants": [{"athlete": {"displayName": "Reece James"}}]}


class NormalizationTests(unittest.TestCase):
    def test_goal_has_real_player_minute_logo_and_score(self):
        item = extract_events({"keyEvents": [goal()]}, fixture(2))[0]
        self.assertEqual(item["type"], "goal")
        self.assertEqual(item["player"], "Bukayo Saka")
        self.assertEqual(item["minute"], "52'")
        self.assertEqual(item["home"]["score"], 2)
        self.assertEqual(item["away"]["name"], "Chelsea")
        self.assertEqual(item["home"]["logo"], "https://a.espncdn.com/a.png")
        self.assertEqual(item["league"], "eng.1")

    def test_fresh_summary_score_overrides_stale_daily_score(self):
        old = fixture(score=1)
        raw = {"header": {"competitions": [{"competitors": [
            {"homeAway": "home", "score": "2"}, {"homeAway": "away", "score": "1"},
        ]}]}}
        result = fixture_score_from_summary(old, raw)
        self.assertEqual((result["home"]["score"], result["away"]["score"]), (2, 1))
        self.assertEqual(old["home"]["score"], 1, "must not mutate cached snapshot")
        self.assertIs(fixture_score_from_summary(old, {}), old)
        self.assertIs(fixture_score_from_summary(old, {"header": {"competitions": [
            {"competitors": [{"homeAway": "home", "score": "bad"}]}
        ]}}), old)

    def test_yellow_and_second_yellow_red(self):
        items = extract_events({"keyEvents": [yellow(), red()]}, fixture())
        self.assertEqual([row["type"] for row in items], ["yellow", "red"])
        self.assertEqual([row["player"] for row in items], ["Reece James"] * 2)

    def test_disallowed_goals_and_missed_penalties_suppressed(self):
        candidates = [{"type": {"text": "Disallowed Goal"}},
                      {"type": {"text": "Penalty Missed"}},
                      {"type": {"text": "VAR - Goal Overturned"}},
                      {"type": {"text": "Goal Kick"}}]
        self.assertEqual([event_kind(x) for x in candidates], [""] * 4)

    def test_missing_timeline_never_resets_baseline(self):
        tracker = LiveEventTracker()
        m = fixture()
        self.assertEqual(tracker.update(m, {}), [])
        self.assertEqual(tracker.update(m, {"keyEvents": [goal()]}), [])
        self.assertEqual(tracker.update(m, {}), [])
        new = tracker.update(m, {"keyEvents": [goal(), yellow()]})
        self.assertEqual([item["type"] for item in new], ["yellow"])

    def test_baseline_emit_dedup_reordering_and_outages(self):
        tracker = LiveEventTracker()
        m = fixture()
        self.assertEqual(tracker.update(m, {"keyEvents": [goal()]}), [])
        new = tracker.update(m, {"keyEvents": [goal(), yellow()]})
        self.assertEqual(len(new), 1)
        self.assertEqual(new[0]["type"], "yellow")
        self.assertTrue(new[0]["published_at"])
        self.assertEqual(tracker.update(m, {"keyEvents": [yellow(), goal()]}), [])
        self.assertEqual(tracker.update(m, {"keyEvents": [goal()]}), [])
        self.assertEqual([item["type"] for item in tracker.update(m, {"keyEvents": [goal(), yellow(), red()]})],
                         ["red"])

    def test_no_historical_replay_and_readded_event(self):
        tracker = LiveEventTracker()
        m = fixture()
        self.assertFalse(tracker.update(m, {"keyEvents": [goal(), yellow()]}))
        self.assertFalse(tracker.update(m, {"keyEvents": [goal()]}))
        self.assertFalse(tracker.update(m, {"keyEvents": [goal(), yellow()]}))
        self.assertEqual([e["type"] for e in tracker.update(m, {"keyEvents": [goal(), red(), yellow()]})], ["red"])
        self.assertEqual(tracker.update({**m, "state": "post"}, {"keyEvents": [goal(), red(), yellow()]}), [])


class CoordinatorLiveEventTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        FakeStore.documents.clear()
        self.events = []
        self.tasks = []
        self.hass = SimpleNamespace(
            bus=SimpleNamespace(async_fire=lambda name, data: self.events.append((name, data))),
            async_create_task=lambda coro: self._task(coro),
        )

    def _task(self, coro):
        t = asyncio.create_task(coro)
        self.tasks.append(t)
        return t

    async def test_refresh_does_not_wait_for_event_fetch_and_emits_verified_events(self):
        permit = asyncio.Event()
        class Provider(MockProvider):
            async def fixtures(self):
                return [fixture()]
            async def summary(self, event_id):
                await permit.wait()
                return {"keyEvents": [goal()]}
            async def live_fixtures(self, days):
                return [fixture()]
        entry = SimpleNamespace(entry_id="events", options={"live_refresh_seconds": 20})
        coord = coordinator_module.FootballNewsCoordinator(self.hass, entry, Provider())
        await asyncio.wait_for(coord._async_update_data(), timeout=1)
        self.assertFalse(permit.is_set(), "coordinator should never wait on ESPN summary")
        permit.set()
        await asyncio.gather(*self.tasks)
        self.assertEqual([name for name, _ in self.events if name == "football_news_live_event"], [])
        async def next_events(_):
            return {"keyEvents": [goal(), yellow(), red()]}
        coord.provider.summary = next_events
        self.tasks.clear()
        await coord._async_update_data()
        await asyncio.gather(*self.tasks)
        alerts = [data for name, data in self.events if name == "football_news_live_event"]
        self.assertEqual([data["type"] for data in alerts], ["yellow", "red"])
        self.assertEqual(alerts[0]["team"], "Chelsea")
        self.tasks.clear()
        await coord._async_update_data()
        await asyncio.gather(*self.tasks)
        self.assertEqual(len([name for name, _ in self.events if name == "football_news_live_event"]), 2)
        await coord.async_stop_live_events()


if __name__ == "__main__":
    unittest.main()
