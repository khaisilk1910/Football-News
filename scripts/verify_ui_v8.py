"""Real Chromium validation of dropdowns, persistent favourites, light/dark themes.
All data is synthetic, not a claim about ESPN availability.
"""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
JS=ROOT/'custom_components/football_news/frontend/panel.js'

async def run():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium', headless=True,args=['--no-sandbox'])
        result={}
        for theme in ('dark','light'):
            page=await browser.new_page(viewport={'width':420,'height':850},device_scale_factor=1)
            errors=[]
            page.on('pageerror',lambda e: errors.append(str(e)))
            await page.goto('about:blank')
            await page.evaluate("""() => { const db = new Map(); Object.defineProperty(window, 'sessionStorage', {configurable:true, value:{getItem:k=>db.get(k)||null,setItem:(k,v)=>db.set(k,v)}}); }""")
            await page.add_script_tag(content=JS.read_text(encoding='utf8'),type='module')
            # Set CSS variables on real host to emulate HA theme inheritance.
            result[theme]=await page.evaluate('''async (theme) => {
              document.documentElement.style.setProperty('--primary-background-color',theme==='dark'?'#151515':'#f4f6f8');
              document.documentElement.style.setProperty('--card-background-color',theme==='dark'?'#262626':'#ffffff');
              document.documentElement.style.setProperty('--primary-text-color',theme==='dark'?'#f5f5f5':'#232323');
              document.documentElement.style.setProperty('--secondary-text-color',theme==='dark'?'#bcbcbc':'#555555');
              document.documentElement.style.setProperty('--divider-color',theme==='dark'?'#454545':'#c8c8c8');
              const db={clubs:[]};
              const server={callWS:async cmd=>{
                if(cmd.type==='football_news/teams')return {teams:[{id:'359',name:'Arsenal',logo:''},{id:'363',name:'Chelsea',logo:''}]};
                if(cmd.type==='football_news/set_favourite'){
                  db.clubs=cmd.enabled?[{id:cmd.team_id,name:cmd.name,league:cmd.league}]:[];
                  return {saved:true,enabled:cmd.enabled,clubs:db.clubs};
                }
                return {admin:true,language:'vi',leagues:[{league_code:'eng.1',name:'Premier League',
                  entry_state:'loaded',runtime_loaded:true,ready:true,errors:[],
                  fixtures:[],standings:[],news:[],updated_at:{fixtures:'2026-11-11T12:00:00Z'}}],
                  preferences:{clubs:db.clubs,matches:[]}};
              }};
              let el=document.createElement('football-news-panel');document.body.appendChild(el);
              el.hass=server;
              await new Promise(resolve=>setTimeout(resolve,100));
              const firstScreen={hasDropdowns:el.shadowRoot.querySelectorAll('select[data-view-select],select[data-league-select]').length===2,
                bannerGone:!el.shadowRoot.querySelector('section.hero,header.top'),
                noEmptyMetrics:!el.shadowRoot.querySelector('.metrics'),
                selectBackground:getComputedStyle(el.shadowRoot.querySelector('[data-view-select]')).backgroundColor,
                selectColor:getComputedStyle(el.shadowRoot.querySelector('[data-view-select]')).color};
              const select=el.shadowRoot.querySelector('[data-view-select]');select.value='clubs';select.dispatchEvent(new Event('change',{bubbles:true}));
              await new Promise(resolve=>setTimeout(resolve,110));
              const chooseClubs=el.tab==='clubs';
              const fav=el.shadowRoot.querySelector('button[data-club="359"]');
              fav.click();await new Promise(resolve=>setTimeout(resolve,110));
              const saved=el.prefs().clubs.length===1&&el.shadowRoot.innerHTML.includes('Đã lưu đội yêu thích');
              const selected=el.shadowRoot.querySelector('[data-view-select]').value;
              el.remove();
              const newer=document.createElement('football-news-panel');document.body.appendChild(newer);newer.hass=server;
              await new Promise(resolve=>setTimeout(resolve,110));
              const restoredTab=newer.tab==='clubs';
              const restoredFav=newer.prefs().clubs.length===1;
              newer.shadowRoot.querySelector('button[data-club="359"]')?.click();
              await new Promise(resolve=>setTimeout(resolve,90));
              return {...firstScreen,chooseClubs,saved,selected,restoredTab,restoredFav,
                removed:newer.prefs().clubs.length===0,toolbarRefresh:!!newer.shadowRoot.querySelector('.ha-toolbar [data-refresh]')};
            }''',theme)
            filename=ROOT.parent/f'football-news-dropdown-{theme}-v8.png'
            await page.screenshot(path=str(filename),full_page=True)
            assert not errors,errors
            checks=result[theme]
            assert checks['hasDropdowns'] and checks['bannerGone'] and checks['noEmptyMetrics']
            assert all(checks[k] for k in ('chooseClubs','saved','restoredTab','restoredFav','removed','toolbarRefresh')),checks
            assert checks['selected']=='clubs'
            await page.close()
        print('BROWSER_V8',json.dumps(result,ensure_ascii=False))
        await browser.close()

if __name__=='__main__':
    asyncio.run(run())
