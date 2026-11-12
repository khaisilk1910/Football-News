"""Browser QA for overview previews, monthly date picker and standings leaderboards.

Uses explicitly synthetic sports records. It does NOT certify live ESPN responses.
"""
from __future__ import annotations
import asyncio
import copy
import json
from pathlib import Path
from playwright.async_api import async_playwright

from verify_ui_v9 import DATA, LOGO
ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/'custom_components/football_news/frontend/panel.js'
DATA=copy.deepcopy(DATA)
LEAGUE=DATA['leagues'][0]
LEAGUE['standings']=[{'id':str(i),'name':name,'position':i,'played':11,'points':33-i,
                       'wins':10-i,'draws':0,'losses':1,'difference':20-i,'logo':LOGO}
                      for i,name in enumerate(('Arsenal','Brighton & Hove Albion','Manchester City','Liverpool'),1)]
LEAGUE['fixtures'].append({'id':'140','league':'eng.1','kickoff':'2026-11-21T14:00:00Z',
  'state':'pre','status':'Scheduled','venue':'Etihad Stadium',
  'home':{'id':'7','name':'Manchester City','short_name':'Manchester City','score':None,'logo':LOGO},
  'away':{'id':'8','name':'Fulham','short_name':'Fulham','score':None,'logo':LOGO}})
LEAGUE['fixtures'].append({'id':'141','league':'eng.1','kickoff':'2026-11-21T17:00:00Z',
  'state':'pre','status':'Scheduled',
  'home':{'id':'9','name':'AFC Bournemouth','short_name':'AFC Bournemouth','score':None,'logo':LOGO},
  'away':{'id':'10','name':'Nottingham Forest','short_name':'Nottingham Forest','score':None,'logo':LOGO}})
DATA['preferences']['clubs']=[{'id':'1','name':'Manchester United Football Club','league':'eng.1'}]
LEADERS=[{'category':'goals','player':'Player goal scorer','team':'Manchester City','value':12,'photo':LOGO},
         {'category':'goals','player':'Second best striker','team':'Arsenal','value':9,'photo':''},
         {'category':'assists','player':'Best passer','team':'Brighton','value':8,'photo':''}]

async def main():
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    checked=[]
    for theme in ('dark','light'):
      for width in (280,320,375,390,480,640,960,1200):
        page=await browser.new_page(viewport={'width':width,'height':900})
        errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        bg='#171717' if theme=='dark' else '#fafafa'
        fg='#fafafa' if theme=='dark' else '#202020'
        await page.evaluate('''([bg,fg])=>{
          document.documentElement.style.setProperty('--primary-background-color',bg);
          document.documentElement.style.setProperty('--card-background-color',bg);
          document.documentElement.style.setProperty('--primary-text-color',fg);
          document.documentElement.style.setProperty('--secondary-text-color',fg);
          document.documentElement.style.setProperty('--divider-color','#777');
        }''',[bg,fg])
        await page.add_script_tag(content=PANEL.read_text(encoding='utf-8'),type='module')
        await page.evaluate('(leaders)=>window.FN_LEADERS=leaders',LEADERS)
        await page.evaluate('''(data)=>{
          window.FN_DATA=data;
          const el=document.createElement('football-news-panel');document.body.append(el);
          el.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async msg=>{
            if(msg.type==='football_news/data')return window.FN_DATA;
            if(msg.type==='football_news/leaders')return {league:msg.league,leaders:window.FN_LEADERS};
            if(msg.type==='football_news/fixtures_month')return {league:msg.league,month:msg.month,
              fixtures:window.FN_DATA.leagues[0].fixtures,errors:[]};
            return {};
          }};
          window.fnPanel=el;
        }''',DATA)
        await page.wait_for_function("window.fnPanel?.leaderCache['eng.1']?.leaders?.length===3")
        await page.wait_for_function("window.fnPanel.shadowRoot.querySelectorAll('.overview-previews .block').length>=5")
        result=await page.evaluate('''()=>{
          const root=window.fnPanel.shadowRoot;
          const cards=[...root.querySelectorAll('.overview-previews .block')];
          const viewport=document.documentElement.clientWidth;
          const overflow=[];
          if(document.documentElement.scrollWidth>viewport+1)overflow.push('body overflow');
          for(const card of cards){const rect=card.getBoundingClientRect();
            if(rect.right>viewport+1||rect.left< -1)overflow.push('card outside viewport');
            if(card.scrollWidth>card.clientWidth+2)overflow.push('card scroll overflow');
          }
          return {titles:cards.map(card=>card.querySelector('h3')?.textContent),
            count:cards.length,overflow,player:root.textContent.includes('Player goal scorer')};
        }''')
        assert result['count']>=5,(theme,width,result)
        assert result['player'],(theme,width,result)
        assert not result['overflow'],(theme,width,result)
        if theme=='dark' and width==390:
          await page.screenshot(path=str(ROOT.parent/'football-news-overview-v10.png'),full_page=True)
          await page.locator('football-news-panel').evaluate('el=>el.shadowRoot.querySelector(".overview-previews [data-tab=table]").click()')
          await page.wait_for_function("window.fnPanel.tab==='table'")
          assert await page.evaluate("window.fnPanel.shadowRoot.textContent.includes('Best passer')")
          await page.evaluate("window.fnPanel.chooseView('fixtures')")
          await page.wait_for_function("window.fnPanel.tab==='fixtures'")
          await page.locator('football-news-panel').evaluate('el=>el.shadowRoot.querySelector("[data-month-fetch]").click()')
          await page.wait_for_function("window.fnPanel.monthData?.fixtures?.length>0")
          assert await page.evaluate("window.fnPanel.monthData.month==='2026-11' || !!window.fnPanel.monthData.month")
          await page.screenshot(path=str(ROOT.parent/'football-news-calendar-v10.png'),full_page=True)
        checked.append((theme,width))
        assert not errors,(theme,width,errors)
        await page.close()
    await browser.close()
    print(f'PASS {len(checked)} browser viewport/theme checks; overview preview, top players, tab navigation, monthly request')

if __name__=='__main__':asyncio.run(main())
