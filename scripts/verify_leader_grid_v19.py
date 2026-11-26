"""Chromium QA: dual columns on desktops, single column on mobile, polished SVG stats."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'custom_components/football_news/frontend/panel.js').read_text(encoding='utf-8')
ROWS=[{'category':category,'player':('Alexandre Fernandez Washington ' if i % 4==0 else 'Player ') + str(i+1),
       'team':('Brighton & Hove Albion' if i%3==0 else 'Manchester City'),
       'value':20-i,'photo':''}
      for category in ('goals','assists') for i in range(15)]
SAMPLE={'language':'vi','admin':True,'leagues':[{'league_code':'eng.1',
 'name':'Premier League','entry_id':'entry1','entry_state':'loaded','runtime_loaded':True,
 'ready':True,'updated_at':{'fixtures':'2026-11-12T00:00:00Z'},'fixtures':[],
 'standings':[],'news':[], 'errors':[]}], 'preferences':{'clubs':[],'matches':[]}}

async def main():
    combos=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        for theme in ('dark','light'):
            for width in (320,390,768,900,1024,1366,1600):
                page=await browser.new_page(viewport={'width':width,'height':900},device_scale_factor=1)
                errors=[]
                page.on('pageerror',lambda err:errors.append(str(err)))
                await page.goto('about:blank')
                await page.evaluate('''t=>{const c=t==='dark'?['#121212','#202020','#fafafa','#999','#555']:['#fafafa','#ffffff','#151515','#666','#ddd'];
                  for(let [i,key] of ['--primary-background-color','--card-background-color','--primary-text-color','--secondary-text-color','--divider-color'].entries())
                    document.documentElement.style.setProperty(key,c[i]);}''',theme)
                await page.add_script_tag(content=JS,type='module')
                await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
                await page.evaluate('''([data,rows])=>{
                    const el=document.createElement('football-news-panel');document.body.append(el);
                    el.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async req=>req.type==='football_news/leaders'?{leaders:rows}:data};
                    window.panel=el;
                  }''',[SAMPLE,ROWS])
                await page.evaluate("window.panel.chooseView('leaders')")
                await page.wait_for_function("window.panel.shadowRoot.querySelectorAll('.leader-section').length===2")
                result=await page.evaluate('''()=>{
                    const root=window.panel.shadowRoot;
                    const sections=[...root.querySelectorAll('.leaders-grid>.leader-section')];
                    const [a,b]=sections.map(s=>s.getBoundingClientRect());
                    const rows=[...root.querySelectorAll('.leader-section .leader-entry')];
                    return {
                      count:sections.length,rows:rows.length,sectionsSameRow:Math.abs(a.top-b.top)<2,
                      horizontalGap:b.left-a.right,verticalGap:b.top-a.bottom,
                      overflow:document.documentElement.scrollWidth-document.documentElement.clientWidth,
                      icons:root.querySelectorAll('.leader-section .player-stat-icon svg').length,
                      gold:root.querySelectorAll('.leader-section .player-stat-icon.gold').length,
                      boot:root.querySelectorAll('.leader-section .assist-icon svg').length,
                      brokenImages:root.querySelectorAll('.leader-section img').length,
                      gridWidth:root.querySelector('.leaders-grid').getBoundingClientRect().width,
                      panelWidth:root.querySelector('.leaders-grid').getBoundingClientRect().width
                    };
                }''')
                assert result['count']==2 and result['rows']==30,(width,theme,result)
                assert result['icons']==30 and result['gold']==2 and result['boot']==15,(width,theme,result)
                assert result['brokenImages']==0 and result['overflow']<=2,(width,theme,result)
                if width>=900:
                    assert result['sectionsSameRow'] and result['horizontalGap']>=8,(width,theme,result)
                else:
                    assert not result['sectionsSameRow'] and result['verticalGap']>=8,(width,theme,result)
                assert not errors,(theme,width,errors)
                if width in (390,1366):
                    await page.screenshot(path=str(ROOT.parent/f'football-news-players-{theme}-{width}-v2026.11.12.7.png'),full_page=True)
                combos.append((theme,width))
                await page.close()
        await browser.close()
        print('PASS',len(combos),'responsive Chromium layouts; 2 columns >=900px, 1 column on mobile; SVG stats, no horizontal overflow')

if __name__=='__main__':
    asyncio.run(main())
