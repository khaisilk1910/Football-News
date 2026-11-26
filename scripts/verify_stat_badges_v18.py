"""Chromium QA: Top 15 goals/assists; gold-silver-bronze boot/ball, small-screen layout."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/'custom_components/football_news/frontend/panel.js').read_text(encoding='utf-8')
ROWS=[{'category':category,'player':f'Player number {i+1} long surname',
       'team':('Brighton & Hove Albion' if i%3==0 else 'Manchester City'),
       'value':20-i,'photo':'https://a.espncdn.com/i/headshots/soccer/players/full/123.png'}
      for category in ('goals','assists') for i in range(18)]
SAMPLE={'language':'vi','admin':True,'leagues':[{'league_code':'eng.1',
 'name':'Premier League','entry_id':'entry1','entry_state':'loaded','runtime_loaded':True,
 'ready':True,'updated_at':{'fixtures':'2026-11-12T00:00:00Z'},'fixtures':[],
 'standings':[],'news':[], 'errors':[]}], 'preferences':{'clubs':[],'matches':[]}}

async def main():
    async with async_playwright() as p:
        browser=await p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        checks=[]
        for theme in ('dark','light'):
          for width in (280,320,390,768):
            page=await browser.new_page(viewport={'width':width,'height':860}, device_scale_factor=1)
            await page.goto('about:blank')
            await page.evaluate('''t=>{let colors=t==='dark'?['#121212','#202020','#fafafa','#999','#555']:['#fafafa','#ffffff','#151515','#666','#ddd'];
              for(let [i,key] of ['--primary-background-color','--card-background-color','--primary-text-color','--secondary-text-color','--divider-color'].entries())document.documentElement.style.setProperty(key,colors[i]);}''',theme)
            await page.add_script_tag(content=JS,type="module")
            await page.wait_for_function("Boolean(customElements.get('football-news-panel'))")
            await page.evaluate('''([data,rows])=>{
              const el=document.createElement('football-news-panel');document.body.append(el);
              el.isConnected;el.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async req=>req.type==='football_news/leaders'?{leaders:rows}:data};
              window.panel=el;
            }''',[SAMPLE,ROWS])
            await page.evaluate("window.panel.chooseView('leaders')")
            await page.wait_for_function("window.panel.shadowRoot.querySelectorAll('.leader-entry').length===30")
            result=await page.evaluate('''()=>{
               const root=window.panel.shadowRoot;
               const rows=[...root.querySelectorAll('.leader-section .leader-entry')];
               return {total:rows.length,images:root.querySelectorAll('.leader-section img').length,
                 medal:[...root.querySelectorAll('.leader-section .gold,.leader-section .silver,.leader-section .bronze')].length,
                 boots:root.querySelectorAll('.leader-section .assist-icon').length,
                 balls:root.querySelectorAll('.leader-section .goal-icon').length,
                 over:rows.filter(r=>r.getBoundingClientRect().right>document.documentElement.clientWidth+2).length,
                 scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth};
            }''')
            assert result['total']==30,(theme,width,result)
            assert result['medal']==6 and result['boots']==15 and result['balls']==15,(theme,width,result)
            assert result['images']==0 and result['over']==0 and result['scroll']<=result['client']+2,(theme,width,result)
            if width==390:
                await page.screenshot(path=str(ROOT.parent/f'football-news-leaders-icons-{theme}-v2026.11.12.6.png'),full_page=True)
            await page.evaluate("window.panel.chooseView('overview')")
            await page.wait_for_function("window.panel.shadowRoot.querySelectorAll('.overview-leader-entry').length===6")
            assert await page.locator('football-news-panel').count()==1
            checks.append((theme,width))
            await page.close()
        await browser.close()
        print('PASS',len(checks),'Chromium combinations; 15+15 leaders, 3+3 Overview, SVG icons and no photo requests')

if __name__=='__main__':asyncio.run(main())
