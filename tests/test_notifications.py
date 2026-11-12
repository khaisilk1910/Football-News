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


if __name__ == "__main__": unittest.main()
