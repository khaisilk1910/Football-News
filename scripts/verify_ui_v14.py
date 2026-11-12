"""Responsive browser regression for simulated leaderboard rows only."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright
from verify_ui_v12 import DATA as FIXTURE_DATA

ROOT=Path(__file__).resolve().parents[1]
PANEL=(ROOT/'custom_components/football_news/frontend/panel.js').read_text()
ROWS=[]
for category,numbers in [('goals',[11,9,7]),('assists',[8,6,4]),
    ('yellow_cards',[5,4,3]),('red_cards',[2,1,1]),
    ('rating',[7.78,7.74,7.71]),('appearances',[10,9,8]),('minutes',[900,870,840])]:
    for i,n in enumerate(numbers):
        ROWS.append({'category':category,'player':['Long Player Name Example','Player Two','Player Three'][i],
                     'team':['Manchester City','Brighton and Hove Albion','Liverpool'][i],
                     'value':n,'source':'ESPN','photo':''})

async def main():
    checked=[]
    async with async_playwright() as pw:
        browser=await pw.chromium.launch(headless=True,executable_path='/usr/bin/chromium',args=['--no-sandbox'])
        for theme in ['dark','light']:
            for width in [320,390,768]:
                page=await browser.new_page(viewport={'width':width,'height':900})
                errors=[]
                page.on('pageerror',lambda error:errors.append(str(error)))
                await page.evaluate('''t=>{
                document.documentElement.style.setProperty('--primary-background-color', t==='dark'?'#151515':'#fff');
                document.documentElement.style.setProperty('--card-background-color', t==='dark'?'#222':'#fff');
                document.documentElement.style.setProperty('--primary-text-color',t==='dark'?'#fff':'#141414');
                document.documentElement.style.setProperty('--secondary-text-color',t==='dark'?'#ddd':'#333');
                document.documentElement.style.setProperty('--divider-color','#888');}''',theme)
                await page.add_script_tag(content=PANEL,type='module')
                await page.evaluate('''([data,rows])=>{
                    const el=document.createElement('football-news-panel'); document.body.append(el);
                    el.hass={config:{time_zone:'Asia/Ho_Chi_Minh'},callWS:async msg=>{
                        if(msg.type==='football_news/data')return data;
                        if(msg.type==='football_news/leaders')return {league:msg.league,leaders:rows};
                        return {};
                    }};
                    window.fnPanel=el;
                }''',[FIXTURE_DATA,ROWS])
                await page.wait_for_function("window.fnPanel?.leagues().length>0")
                await page.evaluate("window.fnPanel.chooseView('leaders')")
                await page.wait_for_function("window.fnPanel.shadowRoot.querySelectorAll('.leader-section').length===7")
                size=await page.evaluate('''()=>{
                    let root=window.fnPanel.shadowRoot;
                    return {pageWidth:document.documentElement.scrollWidth,
                        viewport:document.documentElement.clientWidth,
                        maxRight:Math.max(...[...root.querySelectorAll('.leader-section')].map(el=>el.getBoundingClientRect().right))};
                }''')
                assert size['pageWidth']<=size['viewport']+2,(theme,width,size)
                assert size['maxRight']<=size['viewport']+2,(theme,width,size)
                assert not errors,(theme,width,errors)
                if width==390:
                    await page.screenshot(path=str(ROOT.parent/f'football-news-leaders-{theme}-v14.png'),full_page=True)
                checked.append((theme,width))
                await page.close()
        await browser.close()
    print('PASS',len(checked),'theme/width combinations; seven source-backed categories with no overflow')
if __name__=='__main__':asyncio.run(main())
