"""Regression: cold HA reload can return zero config entries but durable cache exists."""
from __future__ import annotations

import importlib.util
import logging
import sys
import types
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_cold_start_cache import (
    FakeStore, Cold, entry, document, bare_websocket_data_handler,
)

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "football_news"


class RegistryStore:
    documents = {}

    def __init__(self, _hass, _version, key):
        self.key = key

    async def async_load(self):
        return self.documents.get(self.key)

    def async_delay_save(self, make_value, _delay):
        self.documents[self.key] = make_value()


def load_registry():
    modules = {name: types.ModuleType(name) for name in (
        "homeassistant", "homeassistant.helpers", "homeassistant.helpers.storage"
    )}
    modules["homeassistant.helpers.storage"].Store = RegistryStore
    with patch.dict(sys.modules, modules):
        pkg = types.ModuleType("_football_registry_test")
        pkg.__path__ = [str(ROOT)]
        sys.modules[pkg.__name__] = pkg
        for name in ("const", "registry"):
            spec = importlib.util.spec_from_file_location(f"{pkg.__name__}.{name}", ROOT / (name + ".py"))
            mod = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = mod
            spec.loader.exec_module(mod)
        return sys.modules[pkg.__name__ + ".registry"].FootballLeagueRegistry


Registry = load_registry()


class RegistryFallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        RegistryStore.documents.clear()
        FakeStore.documents.clear()
        FakeStore.writes.clear()

    async def test_last_configured_ids_survive_reload_but_remove_with_entry(self):
        a = Registry(object())
        await a.remember([entry("abc", "eng.1")])
        b = Registry(object())
        rows = await b.fallback_entries()
        self.assertEqual([(x.entry_id, x.data["league"]) for x in rows], [("abc", "eng.1")])
        await b.forget("abc")
        self.assertEqual(await Registry(object()).fallback_entries(), [])

    async def test_wss_data_restores_disk_after_config_registry_temporarily_empty(self):
        FakeStore.documents["football_news_cache_abc"] = document()
        registry = Registry(object())
        await registry.remember([entry("abc", "eng.1")])

        class Entries:
            def async_entries(self, domain):
                self_domain = domain
                assert self_domain == "football_news"
                return []

        class Prefs:
            async def read(self):
                return {"clubs": [], "leagues": [], "matches": []}

        class WS:
            user = SimpleNamespace(id="viewer", is_admin=False)

            def send_result(self, _id, result):
                self.payload = result

        hass = SimpleNamespace(config_entries=Entries(), is_running=True,
            data={"football_news": {"entries": {}, "preferences": Prefs(),
                                     "league_registry": Registry(object()),
                                     "cold_cache": Cold.FootballColdStartCache(object())}})
        connection = WS()
        await bare_websocket_data_handler()(hass, connection, {"id": 1})
        self.assertEqual(connection.payload["registry_source"], "saved_ha")
        self.assertFalse(connection.payload["startup_pending"])
        self.assertTrue(connection.payload["registry_fallback"])
        self.assertEqual(connection.payload["configured_count"], 1)
        self.assertEqual(connection.payload["leagues"][0]["fixtures"][0]["id"], "match")
        self.assertEqual(connection.payload["standings"][0]["name"], "Arsenal")

    async def test_damaged_registry_does_not_create_untrusted_cache_keys(self):
        RegistryStore.documents["football_news_league_registry"] = {
            "entries": {"../../root": "eng.1", "valid-id": "eng.1", "other": "wrong.league"}}
        registry = Registry(object())
        self.assertEqual([x.entry_id for x in await registry.fallback_entries()], ["valid-id"])


if __name__ == "__main__":
    unittest.main()
