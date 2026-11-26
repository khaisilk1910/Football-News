"""ESPN side metadata and precise lineup fields survive match detail normalization."""
import importlib.util
import unittest
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / 'custom_components/football_news/models.py'
spec = importlib.util.spec_from_file_location('fn_models_match35', FILE)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)

class MatchComparisonTests(unittest.TestCase):
    def test_preserve_explicit_teams_and_statistics_keys(self):
        data = {'boxscore': {'teams': [
          {'team': {'id':'20','displayName':'Fulham','logos':[{'href':'https://a.espncdn.com/i/teamlogos/soccer/500/370.png'}]}, 'homeAway':'away',
           'statistics':[{'name':'totalShots','label':'Shots','displayValue':'3'}]},
          {'team': {'id':'10','displayName':'Manchester City'}, 'homeAway':'home',
           'statistics':[{'name':'totalShots','label':'Shots','displayValue':'6'}]}
        ]}}
        result=models.normalize_summary(data)['teams']
        self.assertEqual([t['home_away'] for t in result],['away','home'])
        self.assertEqual([t['id'] for t in result],['20','10'])
        self.assertEqual(result[0]['logo'], 'https://a.espncdn.com/i/teamlogos/soccer/500/370.png')
        self.assertEqual([t['statistics'][0]['key'] for t in result],['totalShots','totalShots'])

    def test_keep_source_position_details_without_inventing_role(self):
        data={'rosters':[{'team':{'id':'10','displayName':'Manchester City','logos':[{'href':'https://a.espncdn.com/i/teamlogos/soccer/500/382.png'}]},'roster':[
          {'starter':True,'athlete':{'displayName':'Defender','position':{'abbreviation':'D'}}},
          {'starter':True,'athlete':{'displayName':'Centre back','position':{'displayName':'Centre Back'}}},
          {'starter':False,'formationPosition':'CDM','athlete':{'displayName':'Midfielder','position':{'abbreviation':'M'}}},
          {'starter':True,'athlete':{'displayName':'Not specified'}},
        ]}]}
        lineup=models.normalize_summary(data)['lineups'][0]
        self.assertEqual(lineup['logo'], 'https://a.espncdn.com/i/teamlogos/soccer/500/382.png')
        players=lineup['players']
        self.assertEqual(players[0]['position'],'D')
        self.assertEqual(players[1]['position'],'Centre Back')
        self.assertEqual(players[2]['position_abbr'],'CDM')
        self.assertEqual(players[3]['position'],'')

if __name__=='__main__': unittest.main()
