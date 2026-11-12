"""Persistent and idempotent favourite selection, using a fake HA storage API."""
from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "custom_components" / "football_news"


class StoreStub:
    contents = {}

    def __init__(self, hass, version, key):
        self.key = key

    async def async_load(self):
        import copy
        return copy.deepcopy(self.contents.get(self.key))

    async def async_save(self, value):
        import copy
        self.contents[self.key] = copy.deepcopy(value)


def load_preferences():
    sys.modules.setdefault('homeassistant', types.ModuleType('homeassistant'))
    sys.modules.setdefault('homeassistant.helpers', types.ModuleType('homeassistant.helpers'))
    storage = sys.modules.setdefault('homeassistant.helpers.storage', types.ModuleType('homeassistant.helpers.storage'))
    storage.Store = StoreStub
    package = sys.modules.setdefault('football_news_pref_test', types.ModuleType('football_news_pref_test'))
    package.__path__ = [str(ROOT)]
    for name in ('const', 'preferences'):
        spec = importlib.util.spec_from_file_location(f'football_news_pref_test.{name}', ROOT / f'{name}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    return sys.modules['football_news_pref_test.preferences'].FootballPreferences


Preferences = load_preferences()


class PreferencesTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        StoreStub.contents.clear()
        self.events = []
        self.hass = types.SimpleNamespace(bus=types.SimpleNamespace(async_fire=lambda event: self.events.append(event)))
        self.prefs = Preferences(self.hass)

    async def test_save_reload_and_remove(self):
        saved = await self.prefs.set_club('eng.1', '359', 'Arsenal', True)
        self.assertTrue(saved['saved'])
        self.assertEqual(len(saved['clubs']), 1)
        after_restart = Preferences(self.hass)
        self.assertEqual((await after_restart.read())['clubs'][0]['name'], 'Arsenal')
        removed = await after_restart.set_club('eng.1', '359', '', False)
        self.assertEqual(removed['clubs'], [])
        self.assertEqual((await Preferences(self.hass).read())['clubs'], [])

    async def test_repeated_save_is_idempotent(self):
        for _ in range(3):
            await self.prefs.set_club('eng.1', '359', 'Arsenal', True)
        self.assertEqual(len((await self.prefs.read())['clubs']), 1)
        for _ in range(2):
            await self.prefs.set_club('eng.1', '359', '', False)
        self.assertEqual((await self.prefs.read())['clubs'], [])

    async def test_rename_and_limit(self):
        await self.prefs.set_club('eng.1', '359', 'Arsenal', True)
        await self.prefs.set_club('eng.1', '359', 'Arsenal FC', True)
        self.assertEqual((await self.prefs.read())['clubs'][0]['name'], 'Arsenal FC')
        for i in range(4):
            await self.prefs.set_club('esp.1', str(200+i), f'Team {i}', True)
        with self.assertRaisesRegex(ValueError, 'Maximum 5'):
            await self.prefs.set_club('ger.1', '99', 'Bayern', True)
        self.assertEqual(len((await Preferences(self.hass).read())['clubs']), 5)

    async def test_invalid_ids_not_written(self):
        for value in ('', 'unsafe-id', '99999999999999999999', '１２３'):
            with self.assertRaises(ValueError):
                await self.prefs.set_club('eng.1', value, 'Team', True)
        self.assertEqual((await self.prefs.read())['clubs'], [])


if __name__ == '__main__':
    unittest.main()
