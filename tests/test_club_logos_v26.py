"""ESPN leaderboard data retains club crests and IDs without extra HTTP calls."""
import unittest
from test_provider_fallback import models


class ClubLogoV26Tests(unittest.TestCase):
    def test_espn_club_logo_preserved_for_player(self):
        result=models.normalize_leaders({'categories':[{'name':'goals','leaders':[
            {'athlete':{'id':'12','displayName':'Striker One'},
             'team':{'id':'364','displayName':'Manchester City',
                     'logos':[{'href':'https://a.espncdn.com/i/teamlogos/soccer/500/364.png'}]},
             'value':9}]}]})
        self.assertEqual(result[0]['team_id'],'364')
        self.assertEqual(result[0]['team_logo'],
                         'https://a.espncdn.com/i/teamlogos/soccer/500/364.png')
        self.assertEqual(result[0]['team'],'Manchester City')

    def test_team_logo_dictionary_and_missing_logo(self):
        rows=models.normalize_leaders({'categories':[{'name':'assists','leaders':[
            {'athlete':{'id':'2','displayName':'Playmaker A'},
             'team':{'id':'15','name':'Team A',
                     'logo':{'href':'https://a.espncdn.com/i/teamlogos/soccer/500/15.png'}},
             'value':5},
            {'athlete':{'id':'3','displayName':'Playmaker B'}, 'value':4}
        ]}]})
        self.assertEqual(rows[0]['team_logo'],'https://a.espncdn.com/i/teamlogos/soccer/500/15.png')
        self.assertEqual(rows[1]['team_logo'],'')
        self.assertEqual(rows[1]['team_id'],'')

    def test_external_team_logo_is_not_retained(self):
        payload={'categories':[{'name':'goals','leaders':[
            {'athlete':{'id':'42','displayName':'Player X'},
             'team':{'name':'Example', 'logo':'https://bad.example/track.png'},
             'value':5}]}]}
        self.assertEqual(models.normalize_leaders(payload)[0]['team_logo'], '')

    def test_duplicate_keeps_more_complete_club_identity(self):
        payload={'categories':[{'name':'goals','leaders':[
            {'athlete':{'id':'4','displayName':'Player X'},'team':{'name':'Team X'},'value':7},
            {'athlete':{'id':'4','displayName':'Player X'},
             'team':{'name':'Team X','logo':'https://a.espncdn.com/i/teamlogos/soccer/500/12.png'},
             'value':7}]}]}
        row=models.normalize_leaders(payload)[0]
        self.assertEqual(row['team_logo'],'https://a.espncdn.com/i/teamlogos/soccer/500/12.png')

if __name__=='__main__':unittest.main()
