"""HA-owned UI state: same account across devices, atomic writes and corruption safety."""
from __future__ import annotations

import asyncio
import importlib.util
import sys
import types
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / "custom_components" / "football_news"


class StubStore:
    documents = {}
    fail = False

    def __init__(self, _hass, _version, key):
        self.key = key

    async def async_load(self):
        return deepcopy(self.documents.get(self.key))

    async def async_save(self, value):
        if self.fail:
            raise OSError("disk full")
        self.documents[self.key] = deepcopy(value)


def load():
    modules = {k: types.ModuleType(k) for k in
               ("homeassistant", "homeassistant.helpers", "homeassistant.helpers.storage")}
    modules["homeassistant.helpers.storage"].Store = StubStore
    with patch.dict(sys.modules, modules):
        pkg = types.ModuleType("_football_ui_test")
        pkg.__path__ = [str(COMPONENT)]
        sys.modules[pkg.__name__] = pkg
        for name in ("const", "ui_state"):
            spec = importlib.util.spec_from_file_location(f"{pkg.__name__}.{name}", COMPONENT / f"{name}.py")
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
        return sys.modules["_football_ui_test.ui_state"].FootballUIState


UIState = load()


class ServerUIStateTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        StubStore.documents.clear()
        StubStore.fail = False
        self.events = []
        self.hass = types.SimpleNamespace(bus=types.SimpleNamespace(
            async_fire=lambda name, *args: self.events.append(name)))

    async def test_shared_between_devices_and_restart(self):
        a = UIState(self.hass)
        b = UIState(self.hass)
        first = await a.update("account-1", {"tab": "news", "league": "eng.1", "style": "premier"})
        self.assertEqual(first["revision"], 1)
        self.assertEqual(await b.read("account-1"), first)
        self.assertEqual((await UIState(self.hass).read("account-2"))["style"], "auto")
        self.assertEqual(self.events, ["football_news_ui_state_updated"])
        self.assertEqual((await b.update("account-1", {"tab": "news"}))["revision"], 1)

    async def test_concurrent_field_patches_do_not_lose_other_fields(self):
        store = UIState(self.hass)
        await asyncio.gather(
            store.update("account-1", {"style": "laliga"}),
            store.update("account-1", {"tab": "fixtures"}),
        )
        self.assertEqual(await store.read("account-1"),
                         {"tab": "fixtures", "league": "all", "style": "laliga", "revision": 2})
        self.assertEqual(await UIState(self.hass).read("account-1"), await store.read("account-1"))

    async def test_storage_failure_is_not_acknowledged_or_kept_in_memory(self):
        store = UIState(self.hass)
        await store.update("account-1", {"tab": "news"})
        StubStore.fail = True
        with self.assertRaises(OSError):
            await store.update("account-1", {"style": "seriea"})
        self.assertEqual((await store.read("account-1"))["style"], "auto")
        self.assertEqual((await UIState(self.hass).read("account-1"))["tab"], "news")
        self.assertEqual(len(self.events), 1)

    async def test_invalid_or_corrupted_state_is_sanitized(self):
        StubStore.documents["football_news_ui_state"] = {
            "users": {"bad": {"tab": ["news"], "league": {"unsafe": 1},
                              "style": ["auto"], "revision": -20}}}
        store = UIState(self.hass)
        self.assertEqual(await store.read("bad"),
                         {"tab": "overview", "league": "all", "style": "auto", "revision": 0})
        for change in ({"league": "unknown"}, {"tab": "shell"},
                       {"style": "custom"}, {"x": "y"}, {}):
            with self.assertRaises(ValueError):
                await store.update("bad", change)


if __name__ == "__main__":
    unittest.main()
