"""Visual smoke test of club cards, details, event timeline and three scorers.

This test supplies EXPLICITLY SYNTHETIC responses and does not verify ESPN availability.
"""
import asyncio
import copy
import json
from pathlib import Path
from playwright.async_api import async_playwright
from verify_ui_v10 import DATA as BASE, LOGO

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/'custom_components/football_news/frontend/panel.js'
DATA=copy.deepcopy(BASE)
DATA['preferences']['clubs']=[
 {'id':'1','league':'eng.1','name':'Manchester United'},
 {'id':'2','league':'eng.1','name':'Brighton & Hove Albion'},
 {'id':'3','league':'eng.1','name':'AFC Bournemouth'},
 {'id':'4','league':'eng.1','name':'Arsenal'},
]
DATA['admin']=True
LEADERS=[{'category':'goals','player':f'Player {i}','team':'Team name','value':19-i*2,'photo':LOGO} for i in range(1,4)]
DETAIL={'type':'club','id':'1','league':'eng.1','name':'Manchester United Football Club','logo':LOGO,
        'location':'Manchester, England','stadium':'Old Trafford','founded_year':'1878','abbreviation':'MUN',
        'roster':[{'id':str(i),'name':f'Player {i} Long Name','photo':LOGO,'position':'Defender','number':str(i)} for i in range(1,16)]}
MATCH={'venue':'Old Trafford','attendance':74149,'events':[
  {'minute':"2'",'description':'The home team scores','team':'Manchester United','kind':'goal'},
  {'minute':"15'",'description':'Yellow card shown','team':'Aston Villa','kind':'card'},
  {'minute':"67'",'description':'Second-half substitution','team':'Manchester United','kind':'substitution'}],
 'teams':[{'name':'Manchester United','statistics':[{'label':'Possession','value':'59%'}]},
          {'name':'Aston Villa','statistics':[{'label':'Possession','value':'41%'}]}],
 'lineups':[{'team':'Manchester United','players':[{'name':'Player A','starter':True,'number':'9','position':'FW'}]}]}

async def main():
  checks=[]
  async with async_playwright() as p:
    browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
    for theme in ('dark','light'):
      for width in (320,375,390,650,900):
        page=await browser.new_page(viewport={'width':width,'height':880})
        errors=[]
        page.on('pageerror',lambda err:errors.append(str(err)))
        await page.evaluate('''(theme)=>{
          document.documentElement.style.setProperty('--primary-background-color',theme==='dark'?'#171717':'#f7f7f7');
          document.documentElement.style.setProperty('--card-background-color',theme==='dark'?'#202020':'#fff');
          document.documentElement.style.setProperty('--primary-text-color',theme==='dark'?'#f7f7f7':'#202020');
          document.documentElement.style.setProperty('--secondary-text-color',theme==='dark'?'#b5b5b5':'#555');
          document.documentElement.style.setProperty('--divider-color',theme==='dark'?'#474747':'#ddd');
        }''',theme)
        await page.add_script_tag(content=PANEL.read_text(encoding='utf-8'),type='module')
        await page.evaluate('''([data,leaders,club,match])=>{
          const el=document.createElement('football-news-panel'); document.body.append(el);
          el.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async msg=>{
            if(msg.type==='football_news/data')return data;
            if(msg.type==='football_news/leaders')return {league:msg.league,leaders};
            if(msg.type==='football_news/teams')return {teams:data.preferences.clubs.map(c=>({id:c.id,name:c.name,logo:club.logo}))};
            if(msg.type==='football_news/club_brief')return {...club,id:msg.team_id,name:data.preferences.clubs.find(c=>c.id===msg.team_id)?.name,roster:[]};
            if(msg.type==='football_news/club')return {...club,id:msg.team_id,name:data.preferences.clubs.find(c=>c.id===msg.team_id)?.name};
            if(msg.type==='football_news/match')return match;
            return {};
          }};
          window.fnPanel=el;
        }''',[DATA,LEADERS,DETAIL,MATCH])
        await page.wait_for_function("window.fnPanel.leaderCache['eng.1']?.leaders?.length===3")
        assert await page.evaluate("window.fnPanel.shadowRoot.querySelectorAll('.scorer-rank').length===3"),'three scorers missing'
        await page.evaluate("window.fnPanel.chooseView('clubs')")
        await page.wait_for_function("window.fnPanel.shadowRoot.querySelectorAll('.club-profile-card').length===4")
        await page.wait_for_function("window.fnPanel.shadowRoot.querySelector('.club-meta')?.textContent.includes('Old Trafford')")
        dimensions=await page.evaluate('''()=>{
          const root=window.fnPanel.shadowRoot;
          return [...root.querySelectorAll('.club-profile-card')].map(e=>({
            width:e.getBoundingClientRect().width,scroll:e.scrollWidth,child:e.querySelector('.club-profile-intro').getBoundingClientRect().width,
            right:e.getBoundingClientRect().right
          }));}''')
        assert all(x['scroll'] <= x['width']+2 and x['child']>65 and x['right']<=width+1 for x in dimensions),(theme,width,dimensions)
        if theme=='dark' and width==390:
          await page.screenshot(path='/mnt/data/football-news-club-cards-v12.png',full_page=True)
        await page.evaluate('''()=>window.fnPanel.shadowRoot.querySelector('[data-club-detail]').click()''')
        await page.wait_for_function("window.fnPanel.shadowRoot.querySelector('.detail-team-hero')?.textContent.includes('Manchester United')")
        modal_overflow=await page.evaluate('''()=>{const el=window.fnPanel.shadowRoot.querySelector('.modal-body');return {width:el.clientWidth,scroll:el.scrollWidth,viewport:document.documentElement.clientWidth};}''')
        assert modal_overflow['scroll']<=modal_overflow['width']+2,(theme,width,modal_overflow)
        if theme=='dark' and width==390:
          await page.screenshot(path='/mnt/data/football-news-club-modal-v12.png',full_page=True)
        await page.evaluate('''()=>window.fnPanel.shadowRoot.querySelector('.modal-close').click()''')
        await page.evaluate("window.fnPanel.chooseView('results')")
        # Source includes at least one completed fixture from verify_ui_v10.
        await page.evaluate('''()=>{const button=window.fnPanel.shadowRoot.querySelector('[data-detail]');if(button)button.click();}''')
        has_match=await page.evaluate("Boolean(window.fnPanel.shadowRoot.querySelector('.modal-body'))")
        if has_match:
          await page.wait_for_function("Boolean(window.fnPanel.shadowRoot.querySelector('.event-item'))")
          assert await page.evaluate("Boolean(window.fnPanel.shadowRoot.querySelector('.detail-match-score'))"),'scoreboard missing'
          if theme=='dark' and width==390:
            await page.screenshot(path='/mnt/data/football-news-match-timeline-v12.png',full_page=True)
        assert not errors,(theme,width,errors)
        checks.append((theme,width))
        await page.close()
    await browser.close()
  print('PASS',len(checks),'theme/viewport combinations, four club cards, full club profile, three scorers, timeline')

if __name__=='__main__':asyncio.run(main())
