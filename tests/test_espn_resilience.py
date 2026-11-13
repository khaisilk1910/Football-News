"""ESPN table envelope regressions, fallback, negative cache and disk recovery."""
from __future__ import annotations

import asyncio
import unittest

# Import provider/models with the same isolated package method as the repository tests.
from test_provider_fallback import models, provider


def row(team="Arsenal", ident="359", rank=1, points=27):
    return {"team":{"id":ident,"displayName":team}, "stats": [
        {"name":"rank","value":rank}, {"name":"points","value":points},
        {"name":"gamesPlayed","value":10}]}


class StandingsResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_nested_grouped_tables_have_real_rows(self):
        payload={"children":[{"children":[{"standings":{"entries":[row()]}}]}]}
        normalized=models.normalize_standings(payload)
        self.assertEqual(len(normalized), 1)
        self.assertEqual(normalized[0]["name"], "Arsenal")
        self.assertEqual(normalized[0]["points"], 27)

    async def test_flat_standings_arrays_accepted(self):
        payload={"standings":[row(), row("Brighton", "351", 2, 22)]}
        rows=models.normalize_standings(payload)
        self.assertEqual([entry["name"] for entry in rows],["Arsenal","Brighton"])

    async def test_malformed_metadata_never_caches_empty_as_success(self):
        obj=provider.FootballProvider(None,"eng.1")
        calls=[]
        async def primary(path, params=None):
            calls.append("primary")
            return {"children":[], "season":{"year":2026}}
        async def mirror(path, season):
            calls.append("mirror")
            return {"children":[{"standings":{"entries":[row(),row("Brighton","351",2,22)]}}]}
        obj._json=primary
        obj._json_standings_mirror=mirror
        self.assertEqual((await obj.standings())[0]["name"],"Arsenal")
        self.assertEqual((await obj.standings())[0]["name"],"Arsenal")
        self.assertEqual(calls,["primary","mirror"])

    async def test_both_invalid_do_not_create_false_success(self):
        obj=provider.FootballProvider(None,"eng.1")
        calls=[]
        async def primary(path, params=None):
            calls.append("primary")
            return {"children":[]}
        async def mirror(path, season):
            calls.append("mirror")
            return {}
        obj._json=primary
        obj._json_standings_mirror=mirror
        with self.assertRaises(provider.ProviderError):
            await obj.standings()
        # No repeated calls during cooldown when users repeatedly reload.
        with self.assertRaises(provider.ProviderError):
            await obj.standings()
        self.assertEqual(calls,["primary","mirror"])

    async def test_name_only_rows_do_not_replace_real_statistics(self):
        obj=provider.FootballProvider(None,"eng.1")
        async def primary(path, params=None):
            return {"standings":{"entries":[{"team":{"id":"359","displayName":"Arsenal"}},
                                           {"team":{"id":"351","displayName":"Brighton"}}]}}
        async def mirror(path, season):
            return {"standings":{"entries":[row(),row("Brighton","351",2,22)]}}
        obj._json=primary
        obj._json_standings_mirror=mirror
        values=await obj.standings()
        self.assertEqual(values[0]["points"],27)

    async def test_rate_limit_does_not_trigger_mirror(self):
        obj=provider.FootballProvider(None,"eng.1")
        calls=[]
        async def primary(path, params=None):
            calls.append("primary")
            raise provider.ProviderError("HTTP 429 at standings")
        async def mirror(path, season):
            calls.append("mirror")
            return {"children":[]}
        obj._json=primary
        obj._json_standings_mirror=mirror
        with self.assertRaises(provider.ProviderError):
            await obj.standings()
        self.assertEqual(calls,["primary"])

    async def test_stale_season_table_does_not_override_current_year(self):
        obj=provider.FootballProvider(None,"eng.1")
        calls=[]
        async def primary(path, params=None):
            calls.append("primary")
            return {"season":{"year":2025},"standings":{"entries":[row()]}}
        async def mirror(path, season):
            calls.append("mirror")
            self.assertEqual(season, obj._season_year())
            return {"season":{"year":season},"standings":{"entries":[row("Chelsea","360",1,25),row("Arsenal","359",2,24)]}}
        obj._json=primary
        obj._json_standings_mirror=mirror
        rows=await obj.standings()
        self.assertEqual(rows[0]["name"],"Chelsea")
        self.assertEqual(calls,["primary","mirror"])

    async def test_primary_nested_payload_needs_no_mirror(self):
        obj=provider.FootballProvider(None,"eng.1")
        async def primary(path, params=None):
            return {"children":[{"children":[{"standings":{"entries":[row(),row("Brighton","351",2,22)]}}]}]}
        async def forbidden(path, season):
            self.fail("Mirror called when primary has a valid table")
        obj._json=primary
        obj._json_standings_mirror=forbidden
        self.assertEqual(len(await obj.standings()),2)
