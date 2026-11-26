"""ESPN-only player portrait contract (no paid API or Football Hub required)."""
import unittest
from test_provider_fallback import models
from _football_news_provider_fixture.espn_site_stats import parse_espn_stats_html

CDN = 'https://a.espncdn.com/i/headshots/soccer/players/full/'


class ESPNPortraitTests(unittest.TestCase):
    def test_explicit_espn_photo_overrides_generated_id(self):
        raw = {'id': '45843', 'headshot': {'href': 'https://a.espncdn.com/i/headshots/soccer/players/full/45843.png'}}
        self.assertEqual(models.espn_athlete_photo(raw), CDN + '45843.png')
        self.assertEqual(models.espn_athlete_photo({'id':'500', 'photo': 'https://cdn.espn.com/athlete.webp'}),
                         'https://cdn.espn.com/athlete.webp')

    def test_fallback_from_real_espn_player_id(self):
        payload = {'categories':[{'name':'goals','leaders':[
            {'athlete':{'id':'123456','displayName':'Example Forward'},'value':9}]}]}
        player = models.normalize_leaders(payload)[0]
        self.assertEqual(player['player_id'], '123456')
        self.assertEqual(player['photo'], CDN + '123456.png')
        roster = models.normalize_roster({'athletes':[{'id':'123456','displayName':'Example Forward'}]})
        self.assertEqual(roster[0]['photo'], CDN + '123456.png')

    def test_untrusted_photos_and_untrusted_ids_rejected(self):
        self.assertEqual(models.espn_athlete_photo({'id':'bad/id', 'headshot': {'href':'https://bad.example/a.png'}}),'')
        self.assertEqual(models.espn_athlete_photo({'id':'123','headshot':{'href':'http://a.espncdn.com/a.png'}}),CDN+'123.png')
        self.assertEqual(models.espn_player_id_from_profile('https://evil.example/soccer/player/_/id/1234/x'),'')
        self.assertEqual(models.espn_player_id_from_profile('/soccer/player/_/id/123456/name'),'123456')
        self.assertEqual(models.espn_player_id_from_profile('https://www.espn.com/soccer/player/_/id/45843/lionel-messi'),'45843')

    def test_public_espn_table_profile_creates_athlete_photo(self):
        html = '''<h2>Top Scorers</h2><table><tr><th>RK</th><th>NAME</th><th>TEAM</th><th>G</th></tr>
        <tr><td>1</td><td><a href="/soccer/player/_/id/45843/lionel-messi">Lionel Messi</a></td><td>Team</td><td>11</td></tr></table>'''
        rows = parse_espn_stats_html(html)
        self.assertEqual(rows[0]['player_id'], '45843')
        self.assertEqual(rows[0]['photo'], CDN + '45843.png')

    def test_named_core_reference_id_without_extra_fetch(self):
        import asyncio
        from test_provider_fallback import provider
        root = 'https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/'
        object_ = provider.FootballProvider(None, 'eng.1')
        calls=[]
        async def fail_read(url,params=None):
            calls.append(url)
            return {}
        object_._absolute_json=fail_read
        resolved=asyncio.run(object_._resolve_core_leaders({'categories':[
            {'name':'goals','leaders':[{'athlete':{'displayName':'Named player', '$ref':root+'athletes/1234'},'value':9}]}]}))
        rows=models.normalize_leaders(resolved)
        self.assertEqual(rows[0]['photo'],CDN+'1234.png')
        self.assertEqual(calls,[])

    def test_missing_player_profile_does_not_invent_photo(self):
        html = '''<h2>Top Scorers</h2><table><tr><th>NAME</th><th>G</th></tr>
        <tr><td>Unknown Athlete</td><td>9</td></tr></table>'''
        rows = parse_espn_stats_html(html)
        self.assertEqual(rows[0]['photo'], '')

if __name__ == '__main__': unittest.main()
