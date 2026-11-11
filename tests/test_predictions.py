"""Independent tests for clean-room prediction engines and access rules."""
from __future__ import annotations

import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / 'custom_components/football_news/predictions.py'
spec = importlib.util.spec_from_file_location('football_predictions_test', PATH)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def deadline(seconds):
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def match(fid, home, away, hscore, ascore, state='post'):
    return {'id': str(fid), 'state': state,
            'home': {'id': str(home), 'score': hscore},
            'away': {'id': str(away), 'score': ascore}}


class PredictionTests(unittest.TestCase):
    def test_lms_winning_team_survives_draw_eliminates(self):
        comp = module.new_competition('lms', 'Friends cup', 'eng.1')
        a = module.add_player(comp, 'Alex')
        b = module.add_player(comp, 'Lan')
        module.configure_round(comp, 'r1', deadline(200), ['100', '200'])
        module.submit_pick(comp, 'r1', a, [{'fixture_id':'100', 'team_id':'1'}])
        module.submit_pick(comp, 'r1', b, [{'fixture_id':'200', 'team_id':'3'}])
        comp['rounds']['r1']['deadline'] = deadline(-100)
        self.assertTrue(module.settle(comp, [match('100','1','2',2,0),match('200','3','4',1,1)]))
        self.assertTrue(comp['players'][a]['active'])
        self.assertFalse(comp['players'][b]['active'])
        self.assertTrue(comp['rounds']['r1']['complete'])
        self.assertFalse(module.settle(comp, [match('100','1','2',2,0),match('200','3','4',1,1)]))
        self.assertEqual(len(comp['history']), 1)

    def test_lms_cannot_reuse_team_across_rounds(self):
        comp = module.new_competition('lms','Test','eng.1')
        a = module.add_player(comp,'Alex')
        module.configure_round(comp,'r1',deadline(300),['100'])
        module.configure_round(comp,'r2',deadline(400),['200'])
        module.submit_pick(comp,'r1',a,[{'fixture_id':'100','team_id':'1'}])
        with self.assertRaisesRegex(ValueError, 'cannot be picked'):
            module.submit_pick(comp,'r2',a,[{'fixture_id':'200','team_id':'1'}])

    def test_acca_two_correct_gives_three_one_gives_one(self):
        comp = module.new_competition('acca', 'Acca test', 'eng.1')
        a = module.add_player(comp, 'A')
        b = module.add_player(comp, 'B')
        c = module.add_player(comp, 'C')
        module.configure_round(comp,'w1',deadline(100),['100','200'])
        module.submit_pick(comp,'w1',a,[{'fixture_id':'100','outcome':'H'},{'fixture_id':'200','outcome':'D'}])
        module.submit_pick(comp,'w1',b,[{'fixture_id':'100','outcome':'H'},{'fixture_id':'200','outcome':'A'}])
        module.submit_pick(comp,'w1',c,[{'fixture_id':'100','outcome':'A'},{'fixture_id':'200','outcome':'A'}])
        comp['rounds']['w1']['deadline'] = deadline(-10)
        self.assertTrue(module.settle(comp,[match('100','1','2',3,1),match('200','3','4',0,0)]))
        self.assertEqual(comp['rounds']['w1']['outcomes'][a]['points'],3)
        self.assertEqual(comp['rounds']['w1']['outcomes'][b]['points'],1)
        self.assertEqual(comp['rounds']['w1']['outcomes'][c]['points'],0)
        self.assertEqual([r['points'] for r in module.standings(comp)],[3,1,0])

    def test_incomplete_scores_never_settle(self):
        comp=module.new_competition('lms','Test','eng.1')
        player=module.add_player(comp,'A')
        module.configure_round(comp,'r1',deadline(100),['100'])
        module.submit_pick(comp,'r1',player,[{'fixture_id':'100','team_id':'1'}])
        comp['rounds']['r1']['deadline']=deadline(-30)
        self.assertFalse(module.settle(comp,[match('100','1','2',None,0)]))
        self.assertFalse(module.settle(comp,[match('100','1','2',0,0,'in')]))
        self.assertTrue(comp['players'][player]['active'])
        self.assertFalse(comp['rounds']['r1']['complete'])

    def test_picks_are_hidden_before_deadline(self):
        comp=module.new_competition('lms','Test','eng.1')
        player=module.add_player(comp,'A')
        module.configure_round(comp,'r1',deadline(300),['100'])
        module.submit_pick(comp,'r1',player,[{'fixture_id':'100','team_id':'1'}])
        self.assertEqual(module.public_snapshot(comp)['rounds']['r1']['picks'],{})
        self.assertIn(player,module.public_snapshot(comp,include_pending=True)['rounds']['r1']['picks'])

    def test_deadline_rejects_naive_time(self):
        comp=module.new_competition('lms','Test','eng.1')
        with self.assertRaisesRegex(ValueError,'Invalid deadline'):
            module.configure_round(comp,'r1','2026-11-11T11:00:00',['100'])

    def test_bad_outcome_and_duplicate_fixtures_rejected(self):
        comp=module.new_competition('acca','Test','eng.1')
        player=module.add_player(comp,'A')
        module.configure_round(comp,'r1',deadline(300),['100','200'])
        with self.assertRaises(ValueError):
            module.submit_pick(comp,'r1',player,[{'fixture_id':'100','outcome':'H'},{'fixture_id':'100','outcome':'A'}])
        with self.assertRaises(ValueError):
            module.submit_pick(comp,'r1',player,[{'fixture_id':'100','outcome':'X'},{'fixture_id':'200','outcome':'A'}])

    def test_fixture_outcome_accepts_zero_zero(self):
        self.assertEqual(module.fixture_outcome(match('100','1','2',0,0)),'D')
        self.assertIsNone(module.fixture_outcome(match('100','1','2',None,0)))


if __name__ == '__main__':
    unittest.main()
