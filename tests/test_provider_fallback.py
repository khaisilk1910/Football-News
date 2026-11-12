"""Fixture, month and ESPN leader tests without a running HA instance."""
from __future__ import annotations

import asyncio
import importlib.util
from datetime import datetime, timezone
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / 'custom_components/football_news'
PKG = '_football_news_provider_fixture'
if PKG not in sys.modules:
    package = types.ModuleType(PKG)
    package.__path__ = [str(COMPONENT)]
    sys.modules[PKG] = package
    for basename in ('const', 'models', 'espn_site_stats', 'provider'):
        spec = importlib.util.spec_from_file_location(f'{PKG}.{basename}', COMPONENT / f'{basename}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
provider = sys.modules[f'{PKG}.provider']
models = sys.modules[f'{PKG}.models']


def fixture(event_id: str = '401879245', date: str = '2026-11-21T15:00:00Z'):
    return {'id': event_id, 'date': date, 'status': {'type': {'state': 'pre'}},
            'competitions': [{'competitors': [
                {'homeAway': 'home', 'team': {'id': '1', 'displayName': 'One'}},
                {'homeAway': 'away', 'team': {'id': '2', 'displayName': 'Two'}}]}]}


class FixedDateTime(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 11, 11, tzinfo=timezone.utc)


class ProviderCalendarTests(unittest.TestCase):
    def make(self):
        return provider.FootballProvider(None, 'eng.1')

    def test_calendar_window_uses_supported_month_filter(self):
        obj = self.make()
        calls = []

        async def read(path, params=None):
            calls.append(params['dates'])
            return {'events': []}

        obj._json = read
        with patch.object(provider, 'datetime', FixedDateTime):
            self.assertEqual(asyncio.run(obj.fixtures()), [])
        self.assertEqual(sorted(calls), ['202610', '202611', '202612'])
        self.assertTrue(all(len(item) == 6 for item in calls))

    def test_monthly_calendar_returns_real_matches_and_reuses_cache(self):
        obj = self.make()
        calls = []

        async def read(path, params=None):
            calls.append(params['dates'])
            return {'events': [fixture()]}

        obj._json = read
        with patch.object(provider, 'datetime', FixedDateTime):
            matches = asyncio.run(obj.fixtures_month('2026-11'))
            self.assertEqual(len(matches), 1)
            self.assertEqual(matches[0]['home']['name'], 'One')
            self.assertEqual(asyncio.run(obj.fixtures_month('2026-11')), matches)
        self.assertEqual(calls, ['202611'])

    def test_calendar_includes_real_next_matchday(self):
        obj = self.make()
        calls = []

        async def read(path, params=None):
            calls.append(params['dates'])
            return {'events': [fixture()] if params['dates'] == '202611' else []}

        obj._json = read
        with patch.object(provider, 'datetime', FixedDateTime):
            matches = asyncio.run(obj.fixtures())
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0]['id'], '401879245')
        self.assertEqual(len(calls), 3)

    def test_invalid_month_rejected_before_network(self):
        obj = self.make()
        for value in ('2026-00', '202611', '2026-13', '2026-11-01', 'abcdeef'):
            with self.assertRaises(provider.ProviderError):
                asyncio.run(obj.fixtures_month(value))

    def test_partial_month_outage_retains_real_month(self):
        obj = self.make()

        async def read(path, params=None):
            if params['dates'] == '202611':
                return {'events': [fixture()]}
            raise provider.ProviderError('HTTP 500 scoreboard')

        obj._json = read
        with patch.object(provider, 'datetime', FixedDateTime):
            games = asyncio.run(obj.fixtures())
        self.assertEqual(len(games), 1)

    def test_total_month_failure_propagates_error(self):
        obj = self.make()
        calls = []

        async def read(path, params=None):
            calls.append(params['dates'])
            raise provider.ProviderError('HTTP 429 scoreboard')

        obj._json = read
        with patch.object(provider, 'datetime', FixedDateTime):
            with self.assertRaisesRegex(provider.ProviderError, 'All calendar months'):
                asyncio.run(obj.fixtures())
        self.assertEqual(len(calls), 3)
        self.assertTrue(all(len(value)==6 for value in calls))

    def test_invalid_month_envelope_is_not_an_empty_month(self):
        obj = self.make()

        async def read(path, params=None):
            return {'wrong': 'schema'}

        obj._json = read
        with self.assertRaisesRegex(provider.ProviderError, 'events array missing'):
            asyncio.run(obj.fixtures_month('2026-11'))

    def test_month_filter_excludes_other_month_events(self):
        obj = self.make()

        async def read(path, params=None):
            return {'events': [fixture('1', '2026-11-21T15:00:00Z'),
                               fixture('2', '2026-12-01T15:00:00Z')]}

        obj._json = read
        games = asyncio.run(obj.fixtures_month('2026-11'))
        self.assertEqual([x['id'] for x in games], ['1'])

    def test_scores_missing_are_not_zero(self):
        obj = self.make()
        games = obj._clean_fixtures([fixture(), fixture()])
        self.assertEqual(len(games), 1)
        self.assertIsNone(games[0]['home']['score'])

    def test_team_directory(self):
        teams = models.normalize_teams({'sports': [{'leagues': [{'teams': [
            {'team': {'id': '359', 'displayName': 'Arsenal'}},
            {'team': {'id': '360', 'displayName': 'Chelsea'}},
        ]}]}]})
        self.assertEqual([team['name'] for team in teams], ['Arsenal', 'Chelsea'])

    def test_leaders_group_parsing_does_not_invent_data(self):
        rows = models.normalize_leaders({'leaders': [
            {'name': 'goals', 'leaders': [{'athlete': {'id': '1', 'displayName': 'Player A'},
                                         'team': {'displayName': 'FC A'}, 'value': 12}]},
            {'name': 'assists', 'leaders': [{'athlete': {'id': '2', 'displayName': 'Player B'},
                                           'team': {'displayName': 'FC B'}, 'value': 8}]},
            {'name': 'minutesPlayed', 'leaders': [{'athlete': {'id': '3', 'displayName': 'Player C'},
                                                  'value': 900}]},
        ]})
        self.assertEqual([(x['category'], x['player'], x['value']) for x in rows],
                         [('goals', 'Player A', 12), ('assists', 'Player B', 8), ('minutes', 'Player C', 900)])
        self.assertEqual(models.normalize_leaders({'leaders': [{'name': 'goals',
                            'leaders': [{'athlete': {'displayName': 'Player A'}}]}]}), [])

    def test_byathlete_field_format(self):
        rows = models.normalize_leaders({'athletes': [
            {'athlete': {'id': '4', 'displayName': 'Player D'},
             'team': {'displayName': 'FC D'},
             'statistics': [{'name': 'goals', 'value': 16}, {'name': 'assists', 'value': 5}]},
        ]})
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['value'], 16)

    def test_leaders_uses_web_api_not_at_startup(self):
        obj = self.make()
        requested = []

        async def read(url, params=None):
            requested.append(url)
            return {'leaders': [{'name': 'goals', 'leaders': [{
                'athlete': {'displayName': 'Player A'}, 'value': 7}]}]}

        obj._absolute_json = read
        async def no_site(season):
            return []
        obj._site_stats_html = no_site
        self.assertEqual(asyncio.run(obj.leaders())[0]['value'], 7)
        self.assertIn('seasons/2026/types/2/leaders', requested[0])
        self.assertEqual(len(requested), 4)


if __name__ == '__main__':
    unittest.main()
