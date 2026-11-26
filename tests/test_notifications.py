"""Pure format + opt-in notification logic; HA dependencies replaced by stubs."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "football_news"


def load_under_stub_package():
    ha = sys.modules.setdefault("homeassistant", types.ModuleType("homeassistant"))
    core = sys.modules.setdefault("homeassistant.core", types.ModuleType("homeassistant.core"))
    core.HomeAssistant = type("HomeAssistant", (), {})
    helpers = sys.modules.setdefault("homeassistant.helpers", types.ModuleType("homeassistant.helpers"))
    storage = sys.modules.setdefault("homeassistant.helpers.storage", types.ModuleType("homeassistant.helpers.storage"))
    class MemoryStore:
        values = {}
        def __init__(self, hass, version, key): self.key = key
        async def async_load(self): return MemoryStore.values.get(self.key)
        def async_delay_save(self, factory, delay): MemoryStore.values[self.key] = factory()
    storage.Store = MemoryStore
    pkg = sys.modules.setdefault("football_news_test", types.ModuleType("football_news_test"))
    pkg.__path__ = [str(ROOT)]
    for name in ("const", "notifications"):
        spec = importlib.util.spec_from_file_location("football_news_test." + name, ROOT / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return sys.modules["football_news_test.notifications"], MemoryStore


notice, MemoryStore = load_under_stub_package()


class FakeServices:
    def __init__(self): self.calls = []
    def has_service(self, domain, action): return domain == "zalo_bot" and action == "send_message"
    async def async_call(self, domain, action, data, blocking=False):
        self.calls.append(data)
        assert blocking


class NotificationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        MemoryStore.values.clear()
        self.hass = types.SimpleNamespace(
            services=FakeServices(), config=types.SimpleNamespace(time_zone="Asia/Bangkok")
        )
        self.entry = types.SimpleNamespace(
            entry_id="test", options={"zalo_enabled": True, "zalo_account": "+8412",
                                      "zalo_thread_id": "2036121378794772276", "zalo_thread_type": "1"}
        )
        self.notifier = notice.ZaloNotifier(self.hass, self.entry, "Premier League")
        self.entry.options["goal_alerts"] = True
        self.match = {
            "id": "123", "kickoff": (datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat(),
            "state": "pre", "home": {"name": "Arsenal", "score": None},
            "away": {"name": "Chelsea", "score": None}, "venue": "Emirates",
        }

    async def test_schedule_reminder_once_after_restart(self):
        data = {"fixtures": [self.match], "news": []}
        await self.notifier.process(data)
        self.assertEqual(len(self.hass.services.calls), 1)
        self.assertIn("SẮP THI ĐẤU", self.hass.services.calls[0]["message"])
        self.assertEqual(self.hass.services.calls[0]["thread_id"], "zalo:2036121378794772276")
        await self.notifier.process(data)
        self.assertEqual(len(self.hass.services.calls), 1)
        restarted = notice.ZaloNotifier(self.hass, self.entry, "Premier League")
        await restarted.process(data)
        self.assertEqual(len(self.hass.services.calls), 1)

    async def test_kickoff_and_result_transition(self):
        first = {**self.match, "kickoff": (datetime.now(timezone.utc)+timedelta(hours=4)).isoformat()}
        await self.notifier.process({"fixtures": [first], "news": []})
        self.assertFalse(self.hass.services.calls)
        live = {**first, "state": "in", "home": {"name": "Arsenal", "score": 0}, "away": {"name": "Chelsea", "score": 0}}
        await self.notifier.process({"fixtures": [live], "news": []})
        final = {**live, "state": "post", "home": {"name": "Arsenal", "score": 2}, "away": {"name": "Chelsea", "score": 1}}
        await self.notifier.process({"fixtures": [final], "news": []})
        self.assertEqual(len(self.hass.services.calls), 2)
        self.assertIn("KẾT QUẢ", self.hass.services.calls[-1]["message"])
        await self.notifier.process({"fixtures": [final], "news": []})
        self.assertEqual(len(self.hass.services.calls), 2)

    async def test_disable_zalo_no_delivery(self):
        self.entry.options["zalo_enabled"] = False
        await self.notifier.process({"fixtures": [self.match], "news": []})
        self.assertEqual(len(self.hass.services.calls), 0)

    async def test_invalid_result_cannot_be_sent(self):
        with self.assertRaises(ValueError):
            notice.build_message("result", self.match, "Premier League", timezone.utc)

    @staticmethod
    def summary(score_home=1, score_away=0, *, player="Bukayo Saka", minute="45+2'", team="1"):
        return {
            "header": {"competitions": [{"competitors": [
                {"homeAway": "home", "score": str(score_home)},
                {"homeAway": "away", "score": str(score_away)},
            ]}]},
            "keyEvents": [{"id": "goal-1", "type": {"text": "Goal"},
                           "team": {"id": team, "displayName": "Arsenal" if team == "1" else "Chelsea"},
                           "clock": {"displayValue": minute},
                           "participants": [{"athlete": {"displayName": player}}]}],
        }

    @staticmethod
    def live_match(score_home, score_away):
        return {"id": "123", "league": "eng.1", "state": "in",
                "home": {"id": "1", "name": "Arsenal", "score": score_home},
                "away": {"id": "2", "name": "Chelsea", "score": score_away}}

    def test_goal_details_verified_scorer_and_stoppage_minute(self):
        match = self.live_match(1, 0)
        details = notice.goal_details_from_summary(match, [0, 0], self.summary())
        self.assertEqual(details, [{"team": "Arsenal", "player": "Bukayo Saka", "minute": "45+2'"}])
        message = notice.build_message("goal", match, "Premier League", timezone.utc,
                                       goal_details=details)
        self.assertIn("Cầu thủ: Bukayo Saka", message)
        self.assertIn("Phút: 45+2'", message)
        self.assertIn("Arsenal", message)
        self.assertIn("1 - 0", message)

    def test_never_attribute_old_scorer_from_stale_summary(self):
        match = self.live_match(2, 0)
        # ESPN detail is one goal behind today's scoreboard.
        self.assertEqual(notice.goal_details_from_summary(match, [1, 0], self.summary(1, 0)), [])
        # A new score without an accompanying timeline also cannot be verified.
        self.assertEqual(notice.goal_details_from_summary(match, [1, 0],
                         {"header": self.summary(2, 0)["header"]}), [])

    def test_own_goal_or_incomplete_timeline_falls_back_without_guess(self):
        match = self.live_match(1, 0)
        data = self.summary()
        data["keyEvents"][0]["team"] = {"id": "2", "displayName": "Chelsea"}
        self.assertEqual(notice.goal_details_from_summary(match, [0, 0], data), [])
        fallback = notice.build_message("goal", match, "Premier League", timezone.utc)
        self.assertIn("ESPN chưa xác nhận", fallback)
        self.assertNotIn("Bukayo Saka", fallback)

    def test_goal_with_missing_player_does_not_invent_name(self):
        match = self.live_match(1, 0)
        data = self.summary()
        data["keyEvents"][0]["participants"] = []
        details = notice.goal_details_from_summary(match, [0, 0], data)
        self.assertEqual(details[0]["player"], "")
        message = notice.build_message("goal", match, "Premier League", timezone.utc,
                                       goal_details=details)
        self.assertIn("Cầu thủ: ESPN đang cập nhật", message)

    def test_goal_increment_for_two_clubs_and_team_attribution(self):
        match = self.live_match(1, 1)
        data = self.summary(1, 1)
        data["keyEvents"].append({
            "id": "goal-2", "type": {"text": "Goal"},
            "team": {"id": "2", "displayName": "Chelsea"},
            "clock": {"displayValue": "65'"},
            "participants": [{"athlete": {"displayName": "Cole Palmer"}}],
        })
        details = notice.goal_details_from_summary(match, [0, 0], data)
        self.assertEqual([(g["team"], g["player"]) for g in details],
                         [("Arsenal", "Bukayo Saka"), ("Chelsea", "Cole Palmer")])

    def test_equalizer_names_new_scorer_not_previous_away_scorer(self):
        match = self.live_match(1, 1)
        summary = self.summary(1, 1, player="Erling Haaland", minute="78'", team="1")
        summary["keyEvents"].insert(0, {
            "id": "goal-old", "type": {"text": "Goal"},
            "team": {"id": "2", "displayName": "Chelsea"},
            "clock": {"displayValue": "16'"},
            "participants": [{"athlete": {"displayName": "Cole Palmer"}}],
        })
        details = notice.goal_details_from_summary(match, [0, 1], summary)
        self.assertEqual(details, [{"team": "Arsenal", "player": "Erling Haaland", "minute": "78'"}])

    def test_goal_notification_contains_exact_matching_espn_play_by_play(self):
        """Keep the full goal description visible in Zalo, as on the match page."""
        commentary = ("Goal! Arsenal 1, Chelsea 0. Bukayo Saka (Arsenal) "
                      "left footed shot from outside the box to the top right "
                      "corner. Assisted by Martin Ødegaard following a fast break.")
        match = self.live_match(1, 0)
        summary = self.summary()
        summary["keyEvents"][0]["description"] = commentary
        summary["keyEvents"][0]["text"] = "Goal!"
        details = notice.goal_details_from_summary(match, [0, 0], summary)
        self.assertEqual(details[0]["description"], commentary)
        message = notice.build_message("goal", match, "Premier League", timezone.utc,
                                       goal_details=details)
        self.assertIn("📝 Diễn biến (ESPN):", message)
        self.assertIn(commentary, message)
        self.assertIn("Cầu thủ: Bukayo Saka", message)
        self.assertIn("45+2'", message)
        self.assertIn("1 - 0", message)

    def test_new_goal_description_never_uses_old_goal_commentary(self):
        match = self.live_match(2, 0)
        summary = self.summary(2, 0)
        summary["keyEvents"][0]["text"] = "Goal! Old goal by Bukayo Saka."
        summary["keyEvents"].append({
            "id": "goal-2", "type": {"text": "Goal"},
            "team": {"id": "1", "displayName": "Arsenal"},
            "clock": {"displayValue": "70'"},
            "participants": [{"athlete": {"displayName": "Gabriel Martinelli"}}],
            "text": "Goal! Gabriel Martinelli (Arsenal) right footed shot to the bottom left corner.",
        })
        details = notice.goal_details_from_summary(match, [1, 0], summary)
        self.assertEqual(len(details), 1)
        self.assertIn("Gabriel Martinelli", details[0]["description"])
        message = notice.build_message("goal", match, "Premier League", timezone.utc,
                                       goal_details=details)
        self.assertNotIn("Old goal by Bukayo", message)
        self.assertIn("bottom left corner", message)

    def test_no_verified_score_does_not_leak_stale_commentary(self):
        match = self.live_match(2, 0)
        old_summary = self.summary(1, 0)
        old_summary["keyEvents"][0]["text"] = "Goal! Old first goal details."
        self.assertEqual(notice.goal_details_from_summary(match, [1, 0], old_summary), [])
        message = notice.build_message("goal", match, "Premier League", timezone.utc)
        self.assertNotIn("Old first goal details", message)
        self.assertIn("ESPN chưa xác nhận", message)

    def test_prose_sanitized_and_bounded_for_zalo_rich_text(self):
        match = self.live_match(1, 0)
        details = [{"team": "Arsenal", "player": "Bukayo Saka", "minute": "78'",
                    "description": "Goal! {big}**fake**{/big} " + ("Assisted by Test Player. " * 60)}]
        message = notice.build_message("goal", match, "Premier League", timezone.utc,
                                       goal_details=details)
        self.assertIn("Diễn biến (ESPN):", message)
        self.assertNotIn("{big}**fake**{/big}", message)
        self.assertLess(len(message), 1350)
        self.assertIn("🏆 Premier League", message)

    async def test_zalo_sends_espn_goal_commentary_without_duplicates(self):
        commentary = "Goal! Arsenal 1, Chelsea 0. Bukayo Saka left footed shot. Assisted by Declan Rice."
        class Provider:
            async def summary(self, event_id):
                data = NotificationTests.summary()
                data["keyEvents"][0]["text"] = commentary
                return data
        self.notifier.provider = Provider()
        await self.notifier.process({"fixtures": [self.live_match(0, 0)], "news": []})
        await self.notifier.process({"fixtures": [self.live_match(1, 0)], "news": []})
        await self.notifier.process({"fixtures": [self.live_match(1, 0)], "news": []})
        self.assertEqual(len(self.hass.services.calls), 1)
        self.assertIn(commentary, self.hass.services.calls[0]["message"])

    async def test_zalo_goal_notification_uses_espn_summary_and_deduplicates(self):
        class FakeProvider:
            calls = 0
            async def summary(self, event_id):
                self.calls += 1
                assert event_id == "123"
                return NotificationTests.summary()
        provider = FakeProvider()
        self.notifier.provider = provider
        first = self.live_match(0, 0)
        await self.notifier.process({"fixtures": [first], "news": []})
        self.assertEqual(self.hass.services.calls, [])
        await self.notifier.process({"fixtures": [self.live_match(1, 0)], "news": []})
        self.assertEqual(provider.calls, 1)
        self.assertEqual(len(self.hass.services.calls), 1)
        content = self.hass.services.calls[0]["message"]
        self.assertIn("Bukayo Saka", content)
        self.assertIn("45+2'", content)
        await self.notifier.process({"fixtures": [self.live_match(1, 0)], "news": []})
        self.assertEqual(len(self.hass.services.calls), 1)
        self.assertEqual(provider.calls, 1)

    async def test_failed_espn_summary_still_notifies_score(self):
        class BrokenProvider:
            async def summary(self, event_id):
                raise RuntimeError("ESPN unavailable")
        self.notifier.provider = BrokenProvider()
        await self.notifier.process({"fixtures": [self.live_match(0, 0)], "news": []})
        await self.notifier.process({"fixtures": [self.live_match(1, 0)], "news": []})
        self.assertEqual(len(self.hass.services.calls), 1)
        self.assertIn("ESPN chưa xác nhận", self.hass.services.calls[0]["message"])


if __name__ == "__main__": unittest.main()
