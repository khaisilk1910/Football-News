"""Next-round per-league fixtures for Assist, with bounded recorder attributes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import patch

COMPONENT = Path(__file__).resolve().parents[1] / 'custom_components' / 'football_news'
spec = importlib.util.spec_from_file_location('fn_voice_schedule_test', COMPONENT / 'voice_schedule.py')
voice = importlib.util.module_from_spec(spec)
spec.loader.exec_module(voice)
NOW = datetime(2026, 11, 20, 9, 0, tzinfo=timezone.utc)


def fixture(id, delta, league='eng.1', state='pre', home='Arsenal', away='Chelsea', round=None):
    result = {'id': str(id), 'state': state,
              'kickoff': (NOW + timedelta(days=delta)).isoformat(), 'league': league,
              'home': {'id': str(id) + 'h', 'name': home},
              'away': {'id': str(id) + 'a', 'name': away}}
    if round is not None:
        result['round'] = round
    return result


class VoiceScheduleTest(unittest.TestCase):
    def test_numbered_round_includes_every_match_not_next_30_days(self):
        rows = [fixture(str(i), 1+i/12, round=12, home=f'Club {i}', away=f'Club {i+10}')
                for i in range(10)]
        rows += [fixture('next',7,round=13), fixture('other',2,league='esp.1',round=12),
                 fixture('old',-7,round=11,state='post')]
        result = voice.schedule_next_round(rows, 'eng.1', 'Premier League', 'Asia/Bangkok', NOW)
        self.assertEqual(result['total_matches'], 10)
        self.assertEqual(result['round_number'], 12)
        self.assertEqual(result['round_label'], 'Vòng 12')
        self.assertEqual(result['round_source'], 'espn')
        self.assertEqual(result['matches'][0]['local_time'], '21/11 16:00')
        self.assertNotIn('next', [row['id'] for row in result['matches']])
        self.assertEqual(result['voice_text'].count('gặp'), 10)
        self.assertNotIn('LaLiga', result['voice_text'])

    def test_next_round_may_include_already_played_fixture(self):
        rows=[fixture('done',-1,round=16,state='post'), fixture('left',1,round=16),
              fixture('later',8,round=17)]
        result=voice.schedule_next_round(rows,'eng.1','Premier League',now=NOW)
        self.assertEqual(result['total_matches'],2)
        self.assertEqual(result['upcoming_matches'],1)
        self.assertEqual([item['id'] for item in result['matches']], ['done','left'])

    def test_estimated_group_is_honest_and_does_not_merge_next_week(self):
        rows=[fixture('a',1,home='Arsenal',away='Chelsea'),
              fixture('b',2,home='Liverpool',away='Spurs'),
              fixture('c',9,home='Arsenal',away='Leeds'),
              fixture('d',25,home='Brighton',away='Burnley')]
        result=voice.schedule_next_round(rows,'eng.1','Premier League',now=NOW)
        self.assertEqual(result['round_number'],None)
        self.assertEqual(result['round_source'],'estimated')
        self.assertIn('ước tính',result['round_label'])
        self.assertEqual([r['id'] for r in result['matches']], ['a','b'])

    def test_no_upcoming_round_is_not_a_30_day_schedule(self):
        result=voice.schedule_next_round([fixture('x',-10,state='post')], 'eng.1','Premier League', now=NOW)
        self.assertEqual(result['total_matches'],0)
        self.assertEqual(result['round_source'],'none')
        self.assertIn('chưa có',result['voice_text'])

    def test_invalid_dates_duplicates_and_missing_tz_are_ignored(self):
        rows=[fixture(1,1,round=14),fixture(1,1,round=14),
              {'id':'3','state':'pre','kickoff':'invalid'},
              {'id':'4','state':'pre','kickoff':'2026-11-22T00:00:00'},
              fixture(5,2,league='ger.1',round=14)]
        result=voice.schedule_next_round(rows,'eng.1','Premier League',now=NOW)
        self.assertEqual(result['total_matches'],1)
        self.assertEqual(result['listed_matches'],1)

    def test_attributes_bounded_even_with_hundreds_of_fixtures(self):
        rows=[fixture(str(i), i/100,round=12,home='Very Long Team Name '*8,
                      away='Another Very Long Team Name '*8) for i in range(200)]
        result=voice.schedule_next_round(rows,'eng.1','Premier League',now=NOW)
        self.assertEqual(result['total_matches'],200)
        self.assertTrue(result['truncated'])
        self.assertLessEqual(len(json.dumps(result['matches'],ensure_ascii=True).encode()),voice.MAX_MATCHES_ATTRIBUTE_BYTES)
        self.assertLessEqual(len(json.dumps(result['voice_text'],ensure_ascii=True).encode()),voice.MAX_VOICE_TEXT_BYTES)
        self.assertIn('Còn ',result['voice_text'])

    def test_sensor_is_per_league_and_keeps_existing_unique_id(self):
        from test_thread_safety import fake_modules
        with patch.dict(sys.modules, fake_modules()):
            pkg=types.ModuleType('fn_sensor_test');pkg.__path__=[str(COMPONENT)]
            const=types.ModuleType('fn_sensor_test.const')
            const.DOMAIN='football_news';const.VERSION='test';const.LEAGUES={
                'eng.1':'Premier League','esp.1':'LaLiga'}
            with patch.dict(sys.modules, {'fn_sensor_test':pkg,'fn_sensor_test.const':const,
                                          'fn_sensor_test.voice_schedule':voice}):
                spec=importlib.util.spec_from_file_location('fn_sensor_test.sensor', COMPONENT/'sensor.py')
                module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
                all_fixtures=[fixture(1,1,round=12),fixture(2,2,league='esp.1',round=13)]
                prefs=types.SimpleNamespace(_loaded=True,_data={'clubs':[
                    {'id':'359','league':'eng.1','name':'Arsenal'},
                    {'id':'10','league':'esp.1','name':'Barcelona'}]})
                hass=types.SimpleNamespace(data={'football_news':{'preferences':prefs}},
                                           config=types.SimpleNamespace(time_zone='Asia/Bangkok'))
                for league, match_id, fav_name in [('eng.1','1','Arsenal'),('esp.1','2','Barcelona')]:
                    coordinator=types.SimpleNamespace(hass=hass,provider=types.SimpleNamespace(league=league),
                        data={'fixtures':all_fixtures, 'updated_at':{'fixtures':NOW.isoformat()},
                              'cache_info':{'restored_datasets':['fixtures']}})
                    entry=types.SimpleNamespace(entry_id='entry_'+league)
                    desc=lambda key: next(d for d in module.DESCRIPTIONS if d.key==key)
                    schedule=module.FootballNewsSensor(coordinator,entry,desc('schedule_next_30_days'))
                    favorite=module.FootballNewsSensor(coordinator,entry,desc('favorite_clubs'))
                    upcoming=module.FootballNewsSensor(coordinator,entry,desc('upcoming_matches'))
                    self.assertTrue(schedule.available)
                    with patch.object(module,'schedule_next_round',
                                      side_effect=lambda *args: voice.schedule_next_round(*args,now=NOW)):
                        attrs=schedule.extra_state_attributes
                        self.assertEqual(schedule.native_value,1)
                        self.assertEqual(attrs['league_code'],league)
                        self.assertEqual(attrs['matches'][0]['id'],match_id)
                    self.assertEqual(upcoming.native_value,1)
                    self.assertEqual(favorite.native_value,1)
                    self.assertEqual(favorite.extra_state_attributes['clubs'][0]['name'],fav_name)
                    self.assertEqual(schedule._attr_unique_id, f'entry_{league}_schedule_next_30_days')


if __name__ == '__main__':
    unittest.main()
