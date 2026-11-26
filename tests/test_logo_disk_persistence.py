"""Last good ESPN competition crest survives restart and cannot be spoofed."""
import unittest
from test_disk_cache import FakeStore, DiskCacheTests, cache

class LogoDiskTests(unittest.IsolatedAsyncioTestCase):
    setUp = DiskCacheTests.setUp
    instance = DiskCacheTests.instance
    async def test_verified_logo_saved_and_restored_with_league(self):
        obj=self.instance()
        obj.provider.league_logo='https://a.espncdn.com/i/leaguelogos/soccer/500/23.png'
        await obj._async_update_data()
        doc=FakeStore.documents['football_news_cache_first']
        self.assertEqual(doc['league_logo'],obj.provider.league_logo)
        new=self.instance()
        await new.async_restore_cache()
        self.assertEqual(new.data['league_logo'],obj.provider.league_logo)

    async def test_untrusted_logo_is_not_persisted(self):
        obj=self.instance()
        obj.provider.league_logo='https://untrusted.example/soccer.png'
        await obj._async_update_data()
        doc=FakeStore.documents['football_news_cache_first']
        self.assertEqual(doc['league_logo'],'')
        self.assertEqual(cache.validated_snapshot(doc,'eng.1',season=2026)['league_logo'],'')

if __name__ == '__main__':unittest.main()
