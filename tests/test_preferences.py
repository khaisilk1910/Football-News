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

    async def test_rename_and_limit_per_competition(self):
        await self.prefs.set_club('eng.1', '359', 'Arsenal', True)
        await self.prefs.set_club('eng.1', '359', 'Arsenal FC', True)
        self.assertEqual((await self.prefs.read())['clubs'][0]['name'], 'Arsenal FC')
        for i in range(4):
            await self.prefs.set_club('eng.1', str(200+i), f'English {i}', True)
        # A full Premier League must not prevent adding LaLiga teams.
        for i in range(5):
            await self.prefs.set_club('esp.1', str(300+i), f'Spanish {i}', True)
        with self.assertRaisesRegex(ValueError, 'Maximum 5.*per league'):
            await self.prefs.set_club('eng.1', '999', 'Sixth English club', True)
        with self.assertRaisesRegex(ValueError, 'Maximum 5.*per league'):
            await self.prefs.set_club('esp.1', '999', 'Sixth Spanish club', True)
        self.assertEqual(len((await Preferences(self.hass).read())['clubs']), 10)
        await self.prefs.set_club('ger.1', '99', 'Bayern', True)
        self.assertEqual(len((await self.prefs.read())['clubs']), 11)
        # Removing from one league only frees capacity in that league.
        await self.prefs.set_club('eng.1', '359', '', False)
        await self.prefs.set_club('eng.1', '999', 'New English club', True)
        self.assertEqual(len((await self.prefs.read())['clubs']), 11)

    async def test_legacy_flat_clubs_migrate_without_data_loss(self):
        # The existing HA Store uses a flat list; do not reformat or delete it.
        store_key = 'football_news_preferences'
        StoreStub.contents[store_key] = { 'clubs': [
            {'league': 'eng.1', 'id': str(i), 'name': f'Team {i}'}
            for i in range(1,6)] + [
            {'league': 'esp.1', 'id': str(i), 'name': f'Club {i}'}
            for i in range(6,11)], 'leagues': [], 'matches': []}
        restarted = Preferences(self.hass)
        self.assertEqual(len((await restarted.read())['clubs']), 10)
        await restarted.set_club('ger.1', '11', 'Bayern', True)
        self.assertEqual(len((await Preferences(self.hass).read())['clubs']), 11)

    async def test_more_than_100_clubs_survive_restart(self):
        # 25 competitions x 5 favourites may exceed the old 100-row limit.
        from football_news_pref_test.const import LEAGUES
        for league_index, league in enumerate(LEAGUES):
            for i in range(5):
                await self.prefs.set_club(league, str(league_index * 10 + i + 1), f'Team {i}', True)
        original = (await self.prefs.read())['clubs']
        self.assertGreater(len(original), 100)
        self.assertEqual((await Preferences(self.hass).read())['clubs'], original)

    async def test_toggle_uses_per_league_limit(self):
        for i in range(5):
            await self.prefs.toggle_club('eng.1', str(i + 1), f'Team {i}')
        with self.assertRaisesRegex(ValueError, 'Maximum 5'):
            await self.prefs.toggle_club('eng.1', '123', 'Sixth')
        await self.prefs.toggle_club('esp.1', '123', 'Spanish first')
        self.assertEqual(len((await self.prefs.read())['clubs']), 6)

    async def test_failed_store_write_rolls_back_in_memory_state(self):
        from unittest.mock import AsyncMock, patch
        with patch.object(self.prefs._store, "async_save", new_callable=AsyncMock,
                          side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                await self.prefs.set_club("eng.1", "359", "Arsenal", True)
        self.assertEqual((await self.prefs.read())["clubs"], [])
        self.assertEqual((await Preferences(self.hass).read())["clubs"], [])
        self.assertEqual(self.events, [])

    async def test_invalid_ids_not_written(self):
        for value in ('', 'unsafe-id', '99999999999999999999', '１２３'):
            with self.assertRaises(ValueError):
                await self.prefs.set_club('eng.1', value, 'Team', True)
        self.assertEqual((await self.prefs.read())['clubs'], [])


if __name__ == '__main__':
    unittest.main()
