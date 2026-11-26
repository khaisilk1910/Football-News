"""Per-league ten-match form, no API work at Home Assistant startup."""
import asyncio
from datetime import datetime, timezone, timedelta
import unittest
from unittest.mock import patch
from test_provider_fallback import provider

NOW=datetime(2026,11,20,12,0,tzinfo=timezone.utc)

class FrozenDate(datetime):
    @classmethod
    def now(cls,tz=None):
        return NOW


def match(event_id,day,home='1',away='99',score_a=2,score_b=0,state='post'):
    return {'id':str(event_id),'kickoff':(NOW-timedelta(days=day)).isoformat(),
            'state':state, 'home':{'id':home,'name':f'Club {home}','score':score_a},
            'away':{'id':away,'name':f'Club {away}','score':score_b}}

class FavouriteHistoryTests(unittest.TestCase):
    def test_five_favourites_can_each_have_ten_not_global_ten(self):
        obj=provider.FootballProvider(None,'eng.1')
        calls=[]
        async def month(yyyymm):
            calls.append(yyyymm)
            # Dates distributed over the last 65 days, all within 3 months.
            return [match(f'{team}{idx:03}', 4+idx*6, str(team), '99')
                    for team in range(1,6) for idx in range(10)]
        obj._month_events=month
        with patch.object(provider,'datetime',FrozenDate):
            result=asyncio.run(obj.favourite_form_history(['1','2','3','4','5']))
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['fixtures']),50)
        self.assertLessEqual(len(calls),3)
        self.assertTrue(all(game['state']=='post' for game in result['fixtures']))

    def test_pre_live_invalid_score_and_other_league_team_are_excluded(self):
        obj=provider.FootballProvider(None,'eng.1')
        month_calls=[]
        async def month(yyyymm):
            month_calls.append(yyyymm)
            return [match('1',1,'1','2',2,1), match('2',2,'1','2',state='pre'),
                    match('3',3,'1','2',score_a=None),match('4',4,'3','4')]
        obj._month_events=month
        with patch.object(provider,'datetime',FrozenDate):
            result=asyncio.run(obj.favourite_form_history(['1']))
        self.assertEqual([m['id'] for m in result['fixtures']],['1'])
        self.assertFalse(result['complete'])
        self.assertLessEqual(len(month_calls),9)

    def test_reuses_coordinator_when_ten_already_exist_without_network(self):
        obj=provider.FootballProvider(None,'eng.1')
        async def do_not_request(_month):
            raise AssertionError('No ESPN fetch for a full HA snapshot')
        obj._month_events=do_not_request
        known=[match(str(i+1),i+1) for i in range(10)]
        with patch.object(provider,'datetime',FrozenDate):
            result=asyncio.run(obj.favourite_form_history(['1'],known))
        self.assertTrue(result['complete'])
        self.assertEqual(len(result['fixtures']),10)

    def test_one_failed_month_keeps_valid_results(self):
        obj=provider.FootballProvider(None,'esp.1')
        async def month(yyyymm):
            if yyyymm.endswith('10'):
                raise provider.ProviderError('HTTP 429')
            return [match('42',1)]
        obj._month_events=month
        with patch.object(provider,'datetime',FrozenDate):
            result=asyncio.run(obj.favourite_form_history(['1']))
        self.assertEqual(len(result['fixtures']),1)
        self.assertTrue(result['partial'])
        self.assertFalse(result['complete'])

if __name__=='__main__': unittest.main()
