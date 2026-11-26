"""ESPN-only player statistics: normalization and public table parsing."""
from __future__ import annotations

import asyncio
from unittest.mock import patch
import unittest

from test_provider_fallback import provider, models
from _football_news_provider_fixture.espn_site_stats import parse_espn_stats_html


class ESPNLeaderTests(unittest.TestCase):
    def test_core_leader_categories(self):
        cats=[('goals',[9,7,6]),('assists',[5,4,3]),('yellowCards',[5,4,3]),
              ('redCards',[2,1]),('playerRating',[7.86,7.1]),
              ('appearances',[11,10]),('minutesPlayed',[900,875])]
        payload={'categories':[
            {'name':name, 'leaders':[
                {'athlete':{'id':str(i+1),'displayName':f'{name} Player {i+1}',
                            'headshot':{'href':'https://example.com/1.jpg'}},
                 'team':{'displayName':'Example FC'}, 'value':value}
                for i,value in enumerate(values)]}
            for name,values in cats]}
        rows=models.normalize_leaders(payload)
        for name,values in cats:
            mapping={'yellowCards':'yellow_cards','redCards':'red_cards','playerRating':'rating',
                     'minutesPlayed':'minutes'}
            category=mapping.get(name,name)
            self.assertEqual([r['value'] for r in rows if r['category']==category],values)
        self.assertTrue(all(r['source']=='ESPN' for r in rows))

    def test_rejects_unlabelled_goals_and_invalid_stats(self):
        payload={'categories':[{'name':'shots', 'leaders':[{'athlete':{'displayName':'A'},'value':8}]},
                               {'name':'goals','leaders':[{'athlete':{'displayName':'B'},'value':None}]},
                               {'name':'rating','leaders':[{'athlete':{'displayName':'C'},'value':200}]}]}
        self.assertEqual(models.normalize_leaders(payload),[])

    def test_deduplicates_names_and_keeps_ranked_values(self):
        payload={'categories':[{'name':'goals','leaders':[
            {'athlete':{'id':'22','displayName':'A'},'value':8},
            {'athlete':{'id':'22','displayName':'A'},'value':10}]}]}
        rows=models.normalize_leaders(payload)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['value'],10)

    def test_parse_rendered_site_scoring_table(self):
        html='''<h2>Top Scorers</h2><table><tr><th>RK</th><th>NAME</th><th>TEAM</th><th>P</th><th>G</th></tr>
          <tr><td>1</td><td><a href="/soccer/player/_/id/1/erling">Erling Haaland</a></td>
          <td>Manchester City</td><td>10</td><td>9</td></tr>
          <tr><td>2</td><td>Alexander Isak</td><td>Liverpool</td><td>9</td><td>7</td></tr></table>'''
        rows=parse_espn_stats_html(html)
        self.assertEqual([(r['player'],r['value']) for r in rows],
                         [('Erling Haaland',9),('Alexander Isak',7)])
        self.assertTrue(all(r['source']=='ESPN' for r in rows))

    def test_ignores_unrelated_match_table(self):
        html='<h2>Latest results</h2><table><tr><th>NAME</th><th>G</th></tr><tr><td>A</td><td>3</td></tr></table>'
        self.assertEqual(parse_espn_stats_html(html),[])

    def test_core_season_first(self):
        obj=provider.FootballProvider(None,'eng.1')
        calls=[]
        async def read(url, params=None):
            calls.append(url)
            return {'categories':[{'name':'goals','leaders':[
                {'athlete':{'id':'1','displayName':'A'},'value':8}]}]}
        obj._absolute_json=read
        async def no_site(season):
            return []
        obj._site_stats_html=no_site
        rows=asyncio.run(obj.leaders())
        self.assertEqual(rows[0]['value'],8)
        self.assertIn('/seasons/2026/types/2/leaders', calls[0])
        self.assertEqual(len(calls),4)

    def test_site_fallback_when_json_unavailable(self):
        obj=provider.FootballProvider(None,'eng.1')
        async def fail(url, params=None):
            raise provider.ProviderError('HTTP 404 at leaders')
        async def public_page(season):
            self.assertEqual(season,2026)
            return [{'category':'goals','player':'A','value':9,'player_id':'',
                     'team':'Example FC','photo':'','source':'ESPN'}]
        obj._absolute_json=fail
        obj._site_stats_html=public_page
        self.assertEqual(asyncio.run(obj.leaders())[0]['value'],9)

    def test_access_denied_and_no_data_keeps_error(self):
        obj=provider.FootballProvider(None,'eng.1')
        async def fail(url, params=None):
            raise provider.ProviderError('HTTP 403 at leaders')
        async def no_site(season):
            raise provider.ProviderError('HTTP 403 at ESPN public stats')
        obj._absolute_json=fail
        obj._site_stats_html=no_site
        with self.assertRaises(provider.ProviderError):
            asyncio.run(obj.leaders())

    def test_html_assists_and_cautions_without_mixing_scoring_columns(self):
        html=("""<h2>Top Assists</h2><table><tr><th>RK</th><th>NAME</th><th>TEAM</th><th>P</th><th>A</th></tr>
        <tr><td>1</td><td>Player A</td><td>FC A</td><td>12</td><td>8</td></tr></table>
        <h2>Top Yellow Cards</h2><table><tr><th>RK</th><th>NAME</th><th>TEAM</th><th>YC</th></tr>
        <tr><td>1</td><td>Player B</td><td>FC B</td><td>5</td></tr></table>""")
        rows=parse_espn_stats_html(html)
        self.assertEqual([(r['category'],r['value']) for r in rows],
                         [('assists',8),('yellow_cards',5)])

    def test_no_html_match_for_browser_verification(self):
        content='<html><body>In order to continue, verify that you are not a robot.</body></html>'
        self.assertEqual(parse_espn_stats_html(content),[])

    def test_espn_styled_title_without_h2(self):
        html = """<div class='Table__Title'>Top Scorers</div>
        <table><tr><th>NAME</th><th>TEAM</th><th>G</th></tr>
        <tr><td>Player Alpha</td><td>Club One</td><td>8</td></tr></table>"""
        rows=parse_espn_stats_html(html)
        self.assertEqual([(r['player'],r['value']) for r in rows], [('Player Alpha',8)])

    def test_espn_responsive_split_tables(self):
        html = """<h2>Top Scorers</h2>
        <table><tr><th>RK</th><th>NAME</th><th>TEAM</th></tr>
        <tr><td>1</td><td>Haaland</td><td>Manchester City</td></tr>
        <tr><td>2</td><td>Isak</td><td>Liverpool</td></tr></table>
        <h2>Top Scorers</h2><table><tr><th>P</th><th>G</th></tr>
        <tr><td>10</td><td>9</td></tr><tr><td>9</td><td>7</td></tr></table>"""
        rows = parse_espn_stats_html(html)
        self.assertEqual([(x['player'],x['value']) for x in rows],
                         [('Haaland',9),('Isak',7)])

    def test_core_season_scoped_refs_resolved_concurrently(self):
        obj=provider.FootballProvider(None,'eng.1')
        base='https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/seasons/2026/'
        calls=[]
        async def get(url,params=None):
            calls.append(url)
            return {'id':url.rsplit('/',1)[-1],'displayName':'Player '+url.rsplit('/',1)[-1]}
        obj._absolute_json=get
        payload={'categories':[{'name':'goals','leaders':[{'value':8,
          'athlete':{'$ref':base+'athletes/12'}},{'value':7,
          'athlete':{'$ref':base+'athletes/13'}}]}]}
        resolved=asyncio.run(obj._resolve_core_leaders(payload))
        rows=models.normalize_leaders(resolved)
        self.assertEqual([x['value'] for x in rows],[8,7])
        self.assertEqual(len(calls),2)

    def test_legacy_sources_not_imported(self):
        from pathlib import Path
        base=Path(__file__).resolve().parents[1]/'custom_components/football_news'
        self.assertFalse((base/'api_football.py').exists())
        self.assertFalse((base/'ha_leaders.py').exists())
        cfg=(base/'config_flow.py').read_text()
        self.assertNotIn('api_football_key',cfg)
        self.assertNotIn('use_football_hub_data',cfg)

    def test_html_fills_missing_scorers_from_espn_only(self):
        obj=provider.FootballProvider(None,'eng.1')
        async def read(url, params=None):
            return {'categories':[{'name':'goals','leaders':[
                {'athlete':{'id':'1','displayName':'One'},'value':9}]}]}
        async def site(season):
            return [{'category':'goals','player':'One','value':9,'team':'A','photo':'','player_id':'','source':'ESPN'},
                    {'category':'goals','player':'Two','value':7,'team':'B','photo':'','player_id':'','source':'ESPN'},
                    {'category':'goals','player':'Three','value':6,'team':'C','photo':'','player_id':'','source':'ESPN'}]
        obj._absolute_json=read
        obj._site_stats_html=site
        rows=asyncio.run(obj.leaders())
        self.assertEqual(sorted(r['value'] for r in rows if r['category']=='goals'),[6,7,9])

    def test_provider_has_no_external_auth_parameters(self):
        import inspect
        self.assertEqual(tuple(inspect.signature(provider.FootballProvider).parameters),('session','league'))


if __name__=='__main__':
    unittest.main()
