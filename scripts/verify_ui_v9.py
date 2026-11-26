"""Chromium checks for responsive match cards, persistent snapshot after reload and HA themes."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
PANEL=ROOT/'custom_components/football_news/frontend/panel.js'
LOGO='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyOCIgaGVpZ2h0PSIyOCI+PGNpcmNsZSBjeD0iMTQiIGN5PSIxNCIgcj0iMTMiIGZpbGw9IiNkMzI0NDQiLz48L3N2Zz4='
DATA={
  'admin':True,'language':'vi','preferences':{'clubs':[],'matches':[]},
  'leagues':[{'league_code':'eng.1','name':'Premier League','ready':True,'runtime_loaded':True,
   'entry_state':'loaded','updated_at':{'fixtures':'2026-11-11T18:00:00Z'},'errors':[],
   'fixtures':[
    {'id':'101','league':'eng.1','kickoff':'2026-11-08T21:00:00Z','state':'post','status':'FT','venue':'Old Trafford',
     'home':{'id':'1','name':'Manchester United Football Club','short_name':'Manchester United','score':4,'logo':LOGO},
     'away':{'id':'2','name':'Aston Villa Football Club','short_name':'Aston Villa','score':4,'logo':LOGO}},
    {'id':'102','league':'eng.1','kickoff':'2026-11-08T18:00:00Z','state':'post','status':'FT','venue':'Stadium of Light',
     'home':{'id':'3','name':'Sunderland','short_name':'Sunderland','score':1,'logo':LOGO},
     'away':{'id':'4','name':'Chelsea','short_name':'Chelsea','score':0,'logo':LOGO}},
    {'id':'103','league':'eng.1','kickoff':'2026-11-08T19:00:00Z','state':'post','status':'FT','venue':'Vitality Stadium',
     'home':{'id':'5','name':'AFC Bournemouth','short_name':'Bournemouth','score':2,'logo':LOGO},
     'away':{'id':'6','name':'Brighton and Hove Albion Football Club','short_name':'Brighton & Hove Albion','score':3,'logo':LOGO}},
   ],'standings':[],'news':[]}]
}

async def main():
  async with async_playwright() as p:
        browser=await p.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        all_results=[]
        for theme in ('dark','light'):
          for width in (280,320,360,390,480,800,1200):
            page=await browser.new_page(viewport={'width':width,'height':850},device_scale_factor=1)
            errs=[]
            page.on('pageerror',lambda error: errs.append(str(error)))
            await page.evaluate(f'''(() => {{const data={json.dumps(DATA)};const theme={json.dumps(theme)};
              window.fixtureData=data;
              document.documentElement.style.setProperty('--primary-background-color',theme==='dark'?'#161616':'#f7f7f7');
              document.documentElement.style.setProperty('--card-background-color',theme==='dark'?'#242424':'#ffffff');
              document.documentElement.style.setProperty('--primary-text-color',theme==='dark'?'#f5f5f5':'#171717');
              document.documentElement.style.setProperty('--secondary-text-color',theme==='dark'?'#c1c1c1':'#555555');
              document.documentElement.style.setProperty('--divider-color',theme==='dark'?'#555':'#ccc');
            }})()''')
            await page.evaluate('''() => {const values=new Map(); Object.defineProperty(window,'sessionStorage',{configurable:true,value:{getItem:k=>values.get(k)||null,setItem:(k,v)=>values.set(k,v),removeItem:k=>values.delete(k)}});}''')
            await page.add_script_tag(content=PANEL.read_text(encoding='utf8'),type='module')
            await page.evaluate('''() => {const el=document.createElement('football-news-panel');document.body.append(el);
              const server={callWS:async cmd=>{if(cmd.type==='football_news/data'){
                if(sessionStorage.getItem('fn_mock_offline')==='1')throw Error('Temporary WebSocket outage');
                if(sessionStorage.getItem('fn_mock_cold')==='1'){
                  return {...window.fixtureData,leagues:window.fixtureData.leagues.map(l=>({...l,
                    fixtures:[],news:[],standings:[],updated_at:{},ready:false,runtime_loaded:false}))};
                }
                return window.fixtureData;
              }return {};}};
              window.fnServer=server;el.hass=server;window.fnPanel=el;}''')
            await page.wait_for_function('window.fnPanel && window.fnPanel.leagues().length === 1')
            await page.evaluate("window.fnPanel.chooseView('results')")
            result=await page.evaluate('''() => {
              const el=window.fnPanel, root=el.shadowRoot;
              const matches=[...root.querySelectorAll('.match')];
              const errors=[];
              const vw=document.documentElement.clientWidth;
              if(document.documentElement.scrollWidth>vw+1)errors.push(`document ${document.documentElement.scrollWidth} > ${vw}`);
              for(const card of matches){
                const box=card.getBoundingClientRect();
                if(box.right>vw+1 || box.left < -1)errors.push(`card rect ${box.left},${box.right} outside ${vw}`);
                if(card.scrollWidth>card.clientWidth+2)errors.push(`card overflows ${card.scrollWidth}/${card.clientWidth}`);
                for(const item of card.querySelectorAll('.team-identity span,.score,.matchfoot .detail-btn')){
                  const rect=item.getBoundingClientRect();
                  if(rect.right>box.right+1 || rect.left<box.left-1)errors.push(`item ${item.textContent} outside card`);
                }
              }
              return {width:vw,cards:matches.length,hasHome:!!root.querySelector('.toolbar-home'),errors,
                theme:getComputedStyle(root.querySelector('.match')).backgroundColor};
            }''')
            if width==390 and theme=='dark':
              await page.screenshot(path=str(ROOT.parent/'football-news-results-mobile-v9.png'),full_page=True)
              # Remount the same custom element as HA does on a dashboard reload.
              # sessionStorage retains the snapshot across component recreations.
              await page.evaluate('''() => {sessionStorage.setItem('fn_mock_offline','1');
                window.fnPanel.remove();const next=document.createElement('football-news-panel');
                document.body.append(next);next.hass=window.fnServer;window.fnPanel=next;}''')
              await page.wait_for_function('window.fnPanel && window.fnPanel.error')
              after=await page.evaluate('''() => ({
                cached:window.fnPanel._showingCached, leagues:window.fnPanel.leagues().length,
                tab:window.fnPanel.tab, cards:window.fnPanel.shadowRoot.querySelectorAll('.match').length,
                banner:!!window.fnPanel.shadowRoot.querySelector('.snapshot-notice')
              })''')
              assert after=={'cached':True,'leagues':1,'tab':'results','cards':3,'banner':True},after
              await page.evaluate("sessionStorage.removeItem('fn_mock_offline');window.fnPanel.load()")
              await page.wait_for_function('window.fnPanel && !window.fnPanel._showingCached && window.fnPanel.leagues().length===1')
              result['reload_recovered']=True
              # Coordinator temporarily returns configured leagues without datasets;
              # the panel must retain last-good results, not interpret this as 0 games.
              await page.evaluate("sessionStorage.setItem('fn_mock_cold','1')")
              await page.evaluate('window.fnPanel.load()')
              await page.wait_for_function('window.fnPanel && window.fnPanel._showingCached')
              cold=await page.evaluate('''() => ({cards:window.fnPanel.shadowRoot.querySelectorAll('.match').length,
                stale:!!window.fnPanel.shadowRoot.querySelector('.snapshot-notice'),
                leagues:window.fnPanel.leagues().length})''')
              assert cold=={'cards':3,'stale':True,'leagues':1},cold
              await page.evaluate("sessionStorage.removeItem('fn_mock_cold');window.fnPanel.load()")
              await page.wait_for_function('window.fnPanel && !window.fnPanel._showingCached')
              result['cold_coordinator_recovered']=True
              await page.screenshot(path=str(ROOT.parent/'football-news-results-recovered-v9.png'),full_page=True)
            assert not errs,(theme,width,errs)
            assert not result['errors'] and result['cards']==3 and not result['hasHome'],(theme,width,result)
            all_results.append((theme,width))
            await page.close()
        await browser.close()
        print('PASS',len(all_results),'theme/viewport layouts; reload cache, retry and recovery passed')

if __name__=='__main__':asyncio.run(main())
