"""Only use ranked ESPN season data, not fabricated missing Top-15 athletes."""
import asyncio
import unittest
from test_provider_fallback import provider, models

class LeaderTop15Tests(unittest.TestCase):
    def test_core_ranked_goals_and_assists_accept_fifteen_athletes(self):
        groups=[]
        for cat in ('goals','assists'):
            groups.append({'name':cat,'leaders':[
                {'athlete':{'id':str(i+1000),'displayName':f'{cat} {i}'},
                 'team':{'displayName':'Team'},'value':20-i} for i in range(15)]})
        obj=provider.FootballProvider(None,'eng.1')
        async def no_network(*_args,**_kwargs):
            raise AssertionError('Named athlete rows must not cause network I/O')
        obj._absolute_json=no_network
        resolved=asyncio.run(obj._resolve_core_leaders({'categories':groups}))
        rows=models.normalize_leaders(resolved)
        self.assertEqual(len([x for x in rows if x['category']=='goals']),15)
        self.assertEqual(len([x for x in rows if x['category']=='assists']),15)
        self.assertEqual(len(rows),30)

    def test_missing_espn_stats_never_invents_positions(self):
        rows=models.normalize_leaders({'categories':[{'name':'goals','leaders':[
            {'athlete':{'id':'111','displayName':'One'},'value':9}]}]})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['value'],9)

if __name__=='__main__': unittest.main()
