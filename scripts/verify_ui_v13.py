"""Chromium QA with explicitly simulated source data: autocomplete, rounds, rankings."""
from __future__ import annotations
import asyncio
import copy
from pathlib import Path
from playwright.async_api import async_playwright
from verify_ui_v12 import DATA as BASE, LEADERS

ROOT = Path(__file__).resolve().parents[1]
PANEL = ROOT/'custom_components/football_news/frontend/panel.js'
DATA = copy.deepcopy(BASE)
league = DATA['leagues'][0]
league['fixtures'] = [{
    'id':'fixture'+str(i), 'round':7 if i<2 else 8, 'league':'eng.1',
    'league_name':'Premier League','kickoff':'2026-11-21T19:30:00Z' if i<2 else '2026-11-29T16:30:00Z',
    'state':'pre','home':{'id':str(i),'name':name,'short_name':name},
    'away':{'id':'90','name':'Fulham'},
} for i,name in enumerate(('Manchester City','Manchester United','Arsenal'))]
league['standings'] = [
 {'id':str(i),'name':'Premier League Team '+str(i),'position':i,'points':40-i,
  'played':12,'zone': 'champion' if i==1 else 'champions' if i<=4 else
     'relegation' if i>=18 else ''} for i in range(1,21)]

async def main():
    checked=[]
    async with async_playwright() as playwright:
        browser=await playwright.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for theme in ('dark','light'):
            for width in (320,390,768):
                page=await browser.new_page(viewport={'width':width,'height':860})
                errors=[]
                page.on('pageerror', lambda err:errors.append(str(err)))
                await page.evaluate('''(theme)=>{
                  document.documentElement.style.setProperty('--primary-background-color',theme==='dark'?'#151515':'#fff');
                  document.documentElement.style.setProperty('--card-background-color',theme==='dark'?'#222':'#fff');
                  document.documentElement.style.setProperty('--primary-text-color',theme==='dark'?'#fff':'#171717');
                  document.documentElement.style.setProperty('--secondary-text-color',theme==='dark'?'#ddd':'#444');
                  document.documentElement.style.setProperty('--divider-color','#666');
                }''',theme)
                await page.add_script_tag(content=PANEL.read_text(),type='module')
                await page.evaluate('''([data, leaders])=>{
                  const el=document.createElement('football-news-panel');document.body.append(el);
                  el.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async msg=>{
                    if(msg.type==='football_news/data')return data;
                    if(msg.type==='football_news/leaders')return {league:msg.league,leaders};
                    return {};
                  }};
                  window.fnPanel=el;
                }''',[DATA,LEADERS])
                await page.wait_for_function('window.fnPanel?.leagues().length>0')
                await page.evaluate("window.fnPanel.chooseView('fixtures')")
                await page.wait_for_function("window.fnPanel.shadowRoot.querySelector('.round-navigation')?.textContent.includes('Vòng 7/38')")
                # Input event updates the suggestion list without destroying focus.
                await page.locator('football-news-panel').evaluate("el=>{const input=el.shadowRoot.querySelector('[data-fixture-search]'); input.value='Manchester';input.dispatchEvent(new Event('input',{bubbles:true}));}")
                count=await page.evaluate("window.fnPanel.shadowRoot.querySelectorAll('[data-fixture-suggestion]').length")
                assert count==2,(theme,width,count)
                await page.locator('football-news-panel').evaluate("el=>el.shadowRoot.querySelector('[data-fixture-suggestion]').click()")
                assert await page.evaluate("window.fnPanel.fixtureSearch.includes('Manchester')")
                await page.evaluate("window.fnPanel.chooseView('table')")
                await page.wait_for_function("window.fnPanel.shadowRoot.querySelectorAll('.standing-zone.relegation').length===3")
                assert await page.evaluate("window.fnPanel.shadowRoot.querySelectorAll('.standing-zone.champions').length===3")
                assert await page.evaluate("window.fnPanel.shadowRoot.querySelectorAll('.standing-zone.champion').length===1")
                # Responsive horizontal scroll stays inside the table wrapper.
                size=await page.evaluate("""()=>{
                    let root=window.fnPanel.shadowRoot, wrapper=root.querySelector('.tablewrap');
                    return {viewport:document.documentElement.clientWidth,
                            pageWidth:document.documentElement.scrollWidth,
                            wrapperRight:wrapper.getBoundingClientRect().right};
                }""")
                assert size['pageWidth']<=size['viewport']+2,(theme,width,size)
                assert size['wrapperRight']<=size['viewport']+1,(theme,width,size)
                if theme=='dark' and width==390:
                    await page.screenshot(path=str(ROOT.parent/'football-news-standings-v13.png'),full_page=True)
                    await page.evaluate("window.fnPanel.chooseView('fixtures')")
                    await page.screenshot(path=str(ROOT.parent/'football-news-rounds-v13.png'),full_page=True)
                assert not errors,(theme,width,errors)
                checked.append((theme,width))
                await page.close()
        await browser.close()
    print('PASS',len(checked),'Chromium theme/width combinations, autocomplete, round N/T and colored standings')

if __name__ == '__main__':
    asyncio.run(main())
