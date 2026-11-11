"""Test scoreboard fallback without importing a running Home Assistant instance."""
from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
import sys
import types
import unittest

COMPONENT = Path(__file__).resolve().parents[1] / 'custom_components/football_news'
PKG = '_football_news_provider_fixture'
if PKG not in sys.modules:
    package = types.ModuleType(PKG)
    package.__path__ = [str(COMPONENT)]
    sys.modules[PKG] = package
    for basename in ('const', 'models', 'provider'):
        spec = importlib.util.spec_from_file_location(f'{PKG}.{basename}', COMPONENT / f'{basename}.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
provider_module = sys.modules[f'{PKG}.provider']


class ProviderFallbackTests(unittest.TestCase):
    def test_scoreboard_http_error_falls_back_once(self):
        obj = provider_module.FootballProvider(None, 'eng.1')
        requests = []

        async def read(path, params=None):
            requests.append(params)
            if len(requests) == 1:
                raise provider_module.ProviderError('HTTP 500 at scoreboard')
            return {'events': []}

        obj._json = read
        self.assertEqual(asyncio.run(obj.fixtures()), [])
        self.assertEqual(len(requests), 2)
        self.assertIn('dates', requests[0])
        self.assertNotIn('dates', requests[1])

    def test_rate_limit_does_not_create_extra_requests(self):
        obj = provider_module.FootballProvider(None, 'eng.1')
        calls = []

        async def read(path, params=None):
            calls.append(params)
            raise provider_module.ProviderError('HTTP 429 at scoreboard')

        obj._json = read
        with self.assertRaises(provider_module.ProviderError):
            asyncio.run(obj.fixtures())
        self.assertEqual(len(calls), 1)

    def test_missing_events_can_fallback(self):
        obj = provider_module.FootballProvider(None, 'eng.1')
        calls = []

        async def read(path, params=None):
            calls.append(params)
            return {'wrong': 'schema'} if len(calls) == 1 else {'events': []}

        obj._json = read
        self.assertEqual(asyncio.run(obj.fixtures()), [])
        self.assertEqual(len(calls), 2)


if __name__ == '__main__':
    unittest.main()
