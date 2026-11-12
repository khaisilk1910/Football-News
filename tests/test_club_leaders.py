"""Regression tests for independently fetched club metadata and ESPN goal leaders.

These mocked payloads verify defensive parsing, not a live ESPN availability guarantee.
"""
import asyncio
import unittest
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
from test_provider_fallback import provider, models


class ClubLeaderTests(unittest.TestCase):
    def test_club_venue_founded_and_logo(self):
        payload={'team':{'id':'359','displayName':'Arsenal FC','abbreviation':'ARS',
                 'venue':{'fullName':'Emirates Stadium'},'founded':1886,
                 'logos':[{'href':'https://example.com/arsenal.png'}]}}
        result=models.normalize_club(payload,'eng.1')
        self.assertEqual(result['stadium'],'Emirates Stadium')
        self.assertEqual(result['founded_year'],'1886')
        self.assertEqual(result['name'],'Arsenal FC')

    def test_club_unknown_fields_remain_absent(self):
        result=models.normalize_club({'team':{'id':'17','displayName':'Test Club'}},'eng.1')
        self.assertEqual(result['stadium'],'')
        self.assertEqual(result['founded_year'],'')

    def test_core_category_leaders_with_ref_lookups(self):
        obj=provider.FootballProvider(None,'eng.1')
        base='https://sports.core.api.espn.com/v2/sports/soccer/leagues/eng.1/'
        calls=[]
        async def read(url, params=None):
            calls.append(url)
            if 'statistics/byathlete' in url or url.endswith('/apis/v2/sports/soccer/eng.1/leaders'):
                return {}
            if url.endswith('/types/2/leaders'):
                return {'categories':[{'name':'goals','leaders':[
                    {'athlete':{'$ref':base+'athletes/42'},'team':{'$ref':base+'teams/11'},'value':'14'},
                    {'athlete':{'$ref':base+'athletes/43'},'team':{'$ref':base+'teams/12'},'value':'12'},
                    {'athlete':{'$ref':base+'athletes/44'},'team':{'$ref':base+'teams/13'},'value':'10'}]}]}
            if '/athletes/' in url:
                number=url.split('/')[-1]
                return {'id':number,'displayName':'Player '+number}
            if '/teams/' in url:
                number=url.split('/')[-1]
                return {'displayName':'Team '+number}
            if '/leaders' in url:
                return {}
            raise AssertionError(url)
        obj._absolute_json=read
        async def site_unavailable(season):
            return []  # Tests use a mocked ESPN Core source only.
        obj._site_stats_html=site_unavailable
        rows=asyncio.run(obj.leaders())
        self.assertEqual([r['value'] for r in rows if r['category']=='goals'],[14,12,10])
        self.assertEqual(rows[0]['player'],'Player 42')
        self.assertEqual(len([x for x in calls if '/athletes/' in x]),3)

    def test_no_arbitrary_urls_in_core_refs(self):
        obj=provider.FootballProvider(None,'eng.1')
        called=[]
        async def read(url, params=None):
            called.append(url)
            return {'displayName':'Wrong'}
        obj._absolute_json=read
        rows=asyncio.run(obj._resolve_core_leaders({'categories':[{'name':'goals',
          'leaders':[{'athlete':{'$ref':'https://evil.example/test'},'value':'90'}]}]}))
        self.assertEqual(rows['categories'][0]['leaders'][0]['athlete'],{})
        self.assertEqual(called,[])

    def test_events_keep_type_for_ui_without_guesswork(self):
        result=models.normalize_summary({'keyEvents':[
          {'clock':{'displayValue':"73'"},'type':{'text':'Goal'},'text':'Goal from a set piece'},
          {'clock':{'displayValue':"83'"},'type':{'text':'Yellow Card'},'text':'Yellow card given'},
        ]})
        self.assertEqual([e['kind'] for e in result['events']],['goal','card'])

if __name__=='__main__':unittest.main()
