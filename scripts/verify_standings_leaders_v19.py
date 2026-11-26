"""Browser regression: the same two-column player stat boards inside Standings."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'custom_components/football_news/frontend/panel.js').read_text(encoding='utf-8')
LEADERS = [
    {'category': category, 'player': f'Player {i + 1}',
     'team': 'Manchester City' if i % 2 else 'Brighton & Hove Albion',
     'value': 20-i}
    for category in ('goals', 'assists') for i in range(15)
]
DATA = {'language': 'vi', 'admin': True, 'preferences': {'clubs': [], 'matches': []}, 'leagues': [
    {'league_code':'eng.1','name':'Premier League','entry_id':'one','entry_state':'loaded',
     'runtime_loaded':True, 'ready':True,'fixtures':[], 'standings':[],
     'news':[], 'errors':[], 'updated_at': {'fixtures':'2026-11-12T00:00:00Z'}}
]}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for width in (390, 768, 900, 1366):
            for theme in ('dark', 'light'):
                page = await browser.new_page(viewport={'width': width,'height':900})
                await page.goto('about:blank')
                await page.evaluate('''theme=>{const palette=theme==='dark'?['#121212','#202020','#fafafa','#999','#555']:['#fafafa','#ffffff','#151515','#666','#ddd'];
                  ['--primary-background-color','--card-background-color','--primary-text-color','--secondary-text-color','--divider-color']
                  .forEach((name,i)=>document.documentElement.style.setProperty(name,palette[i]));}''',theme)
                await page.add_script_tag(content=SOURCE,type='module')
                await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
                await page.evaluate('''([data,rows])=>{
                    const element=document.createElement('football-news-panel');document.body.append(element);
                    element.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async request=>request.type==='football_news/leaders'?{leaders:rows}:data};
                    window.footballPanel=element;
                }''',[DATA,LEADERS])
                await page.evaluate("window.footballPanel.chooseView('table')")
                await page.wait_for_function("document.querySelector('football-news-panel').shadowRoot.querySelectorAll('.leaders-grid .leader-section').length===2")
                values=await page.evaluate('''()=>{
                  const root=document.querySelector('football-news-panel').shadowRoot;
                  const sections=[...root.querySelectorAll('.leaders-grid>.leader-section')];
                  const rects=sections.map(x=>x.getBoundingClientRect());
                  return {sameRow:Math.abs(rects[0].top-rects[1].top)<3,
                     overflow:root.querySelector('.main').scrollWidth-root.querySelector('.main').clientWidth,
                     goals:sections[0].querySelectorAll('.leader-entry').length,
                     assists:sections[1].querySelectorAll('.leader-entry').length,
                     images:root.querySelectorAll('.leader-section img').length};
                }''')
                assert values['sameRow']==(width>=1024),(width,theme,values)
                assert values['goals']==15 and values['assists']==15,values
                assert values['overflow']<=2 and values['images']==0,values
                if width==1366 and theme=='dark':
                    await page.screenshot(path=str(ROOT.parent/'football-news-standings-top2-v2026.11.12.7.png'),full_page=True)
                await page.close()
        await browser.close()
        print('PASS 8 Chromium Standings combinations: responsive top scorer + top assists, no overflow')

if __name__ == '__main__':
    asyncio.run(main())
