"""Verify adaptive scheduling, daily ESPN cache, live merger and no UI-bound polling."""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch
from time import monotonic

from test_provider_fallback import provider, fixture
from test_disk_cache import coordinator_module, FakeStore, MockProvider

from pathlib import Path
import importlib.util
import sys
import types

pkg = "_football_news_adaptive_tests"
module_path = Path(__file__).resolve().parents[1] / 'custom_components/football_news/adaptive.py'
spec=importlib.util.spec_from_file_location(pkg, module_path)
adaptive=importlib.util.module_from_spec(spec)
sys.modules[pkg]=adaptive
spec.loader.exec_module(adaptive)


class AdaptivePolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 21, 15, tzinfo=timezone.utc)

    def match(self, state, offset, ident='123'):
        return {'id':ident,'state':state,'kickoff':(self.now+timedelta(minutes=offset)).isoformat()}

    def test_idle_cadence(self):
        self.assertEqual(adaptive.refresh_plan([], self.now).seconds,300)
        self.assertEqual(adaptive.refresh_plan([self.match('pre', 720)],self.now).days,())

    def test_before_and_during_kickoff(self):
        self.assertEqual(adaptive.refresh_plan([self.match('pre', 150)],self.now).seconds,150)
        self.assertEqual(adaptive.refresh_plan([self.match('pre', 50)],self.now).seconds,60)
        self.assertEqual(adaptive.refresh_plan([self.match('pre', 5)],self.now).seconds,30)
        self.assertEqual(adaptive.refresh_plan([self.match('pre', -35)],self.now).seconds,30)

    def test_live_is_fastest_and_not_slower_by_another_match(self):
        plan=adaptive.refresh_plan([self.match('pre',5),self.match('in',-100,'456')],self.now)
        self.assertEqual((plan.mode,plan.seconds),('live',20))
        self.assertEqual(plan.days,('20261121',))
        fast=adaptive.refresh_plan([self.match('in',-20)],self.now,15)
        self.assertEqual(fast.seconds,15)
        self.assertEqual(adaptive.refresh_plan([self.match('in',0)],self.now,1).seconds,20)

    def test_stale_live_flag_does_not_poll_forever(self):
        self.assertEqual(adaptive.refresh_plan([self.match('in',-420)],self.now).seconds,300)

    def test_recent_full_time_then_idle(self):
        plan=adaptive.refresh_plan([self.match('post',-155)],self.now)
        self.assertEqual((plan.mode,plan.seconds),('settling',60))
        self.assertEqual(adaptive.refresh_plan([self.match('post',-300)],self.now).seconds,300)

    def test_midnight_and_invalid_kickoff(self):
        now=self.now.replace(hour=1)
        match={'id':'99','state':'in','kickoff':now.isoformat()}
        self.assertEqual(adaptive.refresh_plan([match],now).days,('20261120','20261121'))
        self.assertEqual(adaptive.refresh_plan([{'id':'100','state':'in','kickoff':'bad'}],now).seconds,20)

    def test_day_updates_override_calendar_only_by_id(self):
        old=[{'id':'one','kickoff':self.now.isoformat(),'home':{'score':0}},
             {'id':'two','kickoff':self.now.isoformat()}]
        new=[{'id':'one','kickoff':self.now.isoformat(),'home':{'score':2}}]
        combined=adaptive.merge_fixtures(old,new)
        self.assertEqual(len(combined),2)
        self.assertEqual(next(x for x in combined if x['id']=='one')['home']['score'],2)


class DailyScoreboardTests(unittest.IsolatedAsyncioTestCase):
    async def test_day_query_and_shared_cache(self):
        obj=provider.FootballProvider(None,'eng.1')
        calls=[]
        async def get(path,params=None):
            calls.append(params['dates'])
            return {'events':[fixture(date='2026-11-21T15:00:00Z')]}
        obj._json=get
        first=await obj.matchday_scoreboard('20261121')
        second=await obj.matchday_scoreboard('20261121')
        self.assertEqual(first,second)
        self.assertEqual(calls,['20261121'])
        self.assertEqual(first[0]['id'],'401879245')

    async def test_day_query_rejects_invalid_date_and_empty_envelope(self):
        obj=provider.FootballProvider(None,'eng.1')
        with self.assertRaises(provider.ProviderError):
            await obj.matchday_scoreboard('20261344')
        async def broken(path,params=None):return {}
        obj._json=broken
        with self.assertRaises(provider.ProviderError):
            await obj.matchday_scoreboard('20261121')

    async def test_match_summary_is_single_flight_for_open_devices(self):
        obj=provider.FootballProvider(None,'eng.1')
        calls=[]
        async def get(path,params=None):
            calls.append(params)
            await asyncio.sleep(0)
            return {'header': {'competitions':[]}}
        obj._json=get
        result=await asyncio.gather(obj.summary('123'),obj.summary('123'),obj.summary('123'))
        self.assertEqual(len(result),3)
        self.assertEqual(len(calls),1)


class AdaptiveCoordinatorTests(unittest.IsolatedAsyncioTestCase):
    async def test_live_poll_updates_scores_without_reloading_month(self):
        from types import SimpleNamespace
        FakeStore.documents.clear()
        class Provider(MockProvider):
            def __init__(self):
                super().__init__()
                self.daily_calls=0
                self.score=2
            async def live_fixtures(self, days):
                self.daily_calls+=1
                return [{'id':'f1','state':'in','kickoff':datetime.now(timezone.utc).isoformat(),
                         'home':{'score':self.score}}]
        obj=Provider()
        hass=SimpleNamespace(bus=SimpleNamespace(async_fire=lambda *args:None),
                             async_create_task=lambda coro:asyncio.create_task(coro))
        entry=SimpleNamespace(entry_id='adaptive-live',options={'live_refresh_seconds':15})
        coordinator=coordinator_module.FootballNewsCoordinator(hass,entry,obj)
        now=datetime.now(timezone.utc)
        coordinator._data['fixtures']=[{'id':'f1','state':'in','kickoff':now.isoformat(),'home':{'score':1}}]
        coordinator._dataset_updates['fixtures']=now
        coordinator._calendar_checked_at=monotonic()
        snapshot=await coordinator._async_update_data()
        self.assertEqual(snapshot['fixtures'][0]['home']['score'],2)
        self.assertEqual(snapshot['refresh_policy']['mode'],'live')
        self.assertEqual(snapshot['refresh_policy']['seconds'],15)
        self.assertEqual(obj.calls,0,'fast path must not request the full calendar')
        self.assertEqual(obj.daily_calls,1)
        obj.score=3
        snapshot=await coordinator._async_update_data()
        self.assertEqual(snapshot['fixtures'][0]['home']['score'],3)
        self.assertEqual(obj.calls,0)

    async def test_live_scoreboard_failure_preserves_last_score(self):
        from types import SimpleNamespace
        class Provider(MockProvider):
            async def live_fixtures(self, days):
                raise OSError('upstream offline')
        obj=Provider()
        hass=SimpleNamespace(bus=SimpleNamespace(async_fire=lambda *args:None),
                             async_create_task=lambda coro:asyncio.create_task(coro))
        coordinator=coordinator_module.FootballNewsCoordinator(
            hass,SimpleNamespace(entry_id='adaptive-outage',options={}),obj)
        now=datetime.now(timezone.utc)
        coordinator._data['fixtures']=[{'id':'f1','state':'in','kickoff':now.isoformat(),'home':{'score':2}}]
        coordinator._dataset_updates['fixtures']=now
        coordinator._calendar_checked_at=monotonic()
        output=await coordinator._async_update_data()
        self.assertEqual(output['fixtures'][0]['home']['score'],2)
        self.assertEqual(output['refresh_policy']['mode'],'live')
        self.assertEqual(coordinator.update_interval.total_seconds(),20)


if __name__ == '__main__': unittest.main()
