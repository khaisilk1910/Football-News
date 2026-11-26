"""Match sheet groups and position identity: never guess inactive players."""
from __future__ import annotations
import importlib.util
import unittest
from pathlib import Path

FILE = Path(__file__).resolve().parents[1] / 'custom_components/football_news/models.py'
spec = importlib.util.spec_from_file_location('football_models_lineups', FILE)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)

class MatchSheetTests(unittest.TestCase):
    def test_starters_subs_and_explicit_inactive_not_conflated(self):
        payload = {'rosters':[{'team':{'id':'65','displayName':'Manchester City'},'roster':[
            {'starter':True,'athlete':{'id':'7','displayName':'First GK','jersey':'1',
                                       'position':{'abbreviation':'GK'}}},
            {'starter':False,'athlete':{'id':'8','displayName':'Sub CF','jersey':'9',
                                       'position':{'abbreviation':'CF'}}},
            {'starter':False,'status':'inactive','athlete':{'id':'9','displayName':'Not named',
                                       'position':{'abbreviation':'CB'}}},
        ]}]}
        entry=models.normalize_summary(payload)['lineups'][0]
        self.assertEqual(entry['team_id'],'65')
        self.assertEqual([p['status'] for p in entry['players']],
                         ['starter','substitute','unlisted'])
        self.assertEqual([p['position'] for p in entry['players']],['GK','CF','CB'])
        self.assertEqual([p['id'] for p in entry['players']],['7','8','9'])

    def test_season_squad_has_short_position_as_well_as_display_name(self):
        roster=models.normalize_roster({'athletes':[{'id':'7','displayName':'Goal Keeper',
               'position':{'displayName':'Goalkeeper','abbreviation':'GK'}}]})
        self.assertEqual(roster[0]['position'],'Goalkeeper')
        self.assertEqual(roster[0]['position_abbr'],'GK')

    def test_late_event_survives_more_than_60_commentary_items(self):
        payload={"keyEvents":[{"text":f"Incident {i}","clock":{"displayValue":str(i)}}
                              for i in range(85)]}
        events=models.normalize_summary(payload)['events']
        self.assertEqual(len(events),85)
        self.assertEqual(events[-1]['description'],'Incident 84')

    def test_no_member_status_is_not_guessed_as_absent(self):
        result=models.normalize_summary({'rosters':[{'team':{'id':'1'},'roster':[
            {'athlete':{'id':'3','displayName':'Bench player'}}]}]})
        self.assertEqual(result['lineups'][0]['players'][0]['status'],'substitute')

if __name__ == '__main__': unittest.main()
