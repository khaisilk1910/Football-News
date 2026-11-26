"""Chromium smoke: goal/card popups and responsive layout with simulated ESPN."""
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT/'custom_components/football_news/frontend/panel.js').read_text()

async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width, height, name in ((1440,900,'desktop'),(390,844,'mobile')):
            page = await browser.new_page(viewport={'width':width,'height':height}, device_scale_factor=1)
            errors=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            async def image_reply(route):
                color='#a5264d' if 'arsenal' in route.request.url else '#3670ce'
                svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="45" fill="{color}" stroke="#fff" stroke-width="5"/><path d="M24 50L50 19L76 50L50 81Z" fill="#fff"/></svg>'
                await route.fulfill(status=200,content_type='image/svg+xml',body=svg)
            await page.route('https://logos.example/**',image_reply)
            await page.goto('about:blank')
            await page.add_script_tag(content=JS,type='module')
            await page.evaluate('''async () => {
              await customElements.whenDefined('football-news-panel');
              const fixture={id:'123',league:'eng.1',state:'in',kickoff:new Date().toISOString(),
                home:{name:'Arsenal',score:2,logo:'https://logos.example/arsenal.svg'},
                away:{name:'Chelsea',score:1,logo:'https://logos.example/chelsea.svg'}};
              const panel=document.createElement('football-news-panel');
              document.body.style.margin='0';document.body.appendChild(panel);
              panel.hass={config:{time_zone:'Asia/Bangkok'},user:{is_admin:true},
                connection:{subscribeEvents:async()=>()=>{}},
                callWS:async command=>command.type==='football_news/data'?{
                leagues:[{league_code:'eng.1',name:'Premier League',fixtures:[fixture],news:[],standings:[],
                  updated_at:{fixtures:new Date().toISOString()},attempted:true,ready:true,runtime_loaded:true}],
                preferences:{clubs:[],matches:[]},language:'vi',admin:true}: {events:[],leaders:[]}};
              window.thePanel=panel;
              await new Promise(resolve=>setTimeout(resolve,250));
              panel.receiveLiveEvent({type:'goal',event_key:'123:goal1',event_id:'123',league:'eng.1',
                 league_name:'Premier League',minute:"58'",player:'Bukayo Saka',team:'Arsenal',
                 home:fixture.home,away:fixture.away,published_at:new Date().toISOString()});
              panel.receiveLiveEvent({type:'yellow',event_key:'123:yellow1',event_id:'123',league:'eng.1',
                 league_name:'Premier League',minute:"63'",player:'Reece James',team:'Chelsea',
                 home:fixture.home,away:fixture.away,published_at:new Date().toISOString()});
            }''')
            await page.wait_for_timeout(400)
            cards = page.locator('football-news-panel .fn-live-popup')
            assert await cards.count()==2, 'Both popup events must be visible'
            assert await cards.first.locator('.fn-live-score b').inner_text()=='2 : 1'
            assert await cards.first.locator('.fn-live-club img').count()==2
            assert not errors,errors
            await page.screenshot(path=f'/mnt/data/football-news-live-popup-{name}-preview.png',full_page=False)
            print(f'{name}: goal + yellow card with crests, score, minute and player; JS errors={len(errors)}')
            await page.close()
        await browser.close()

if __name__=='__main__':
    asyncio.run(main())
